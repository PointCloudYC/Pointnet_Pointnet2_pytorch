import torch
import torch.nn as nn
import torch.nn.functional as F
from time import time
import numpy as np

def timeit(tag, t):
    print("{}: {}s".format(tag, time() - t))
    return time()

def pc_normalize(pc):
    l = pc.shape[0]
    centroid = np.mean(pc, axis=0)
    pc = pc - centroid
    m = np.max(np.sqrt(np.sum(pc**2, axis=1))) # get max distance to centroid
    pc = pc / m
    return pc

def square_distance(src, dst):
    """
    Calculate Euclid distance between each two points.

    src^T * dst = xn * xm + yn * ym + zn * zm；
    sum(src^2, dim=-1) = xn*xn + yn*yn + zn*zn;
    sum(dst^2, dim=-1) = xm*xm + ym*ym + zm*zm;
    dist = (xn - xm)^2 + (yn - ym)^2 + (zn - zm)^2
         = sum(src**2,dim=-1)+sum(dst**2,dim=-1)-2*src^T*dst

    Input:
        src: source points, [B, N, C]
        dst: target points, [B, M, C]
    Output:
        dist: per-point square distance, [B, N, M]
    """
    B, N, _ = src.shape
    _, M, _ = dst.shape
    dist = -2 * torch.matmul(src, dst.permute(0, 2, 1))
    dist += torch.sum(src ** 2, -1).view(B, N, 1)
    dist += torch.sum(dst ** 2, -1).view(B, 1, M)
    return dist


def index_points(points, idx):
    """

    Input:
        points: input points data, [B, N, C]
        idx: sample index data, [B, S]
    Return:
        new_points:, indexed points data, [B, S, C]
    """
    device = points.device
    B = points.shape[0]
    view_shape = list(idx.shape)
    view_shape[1:] = [1] * (len(view_shape) - 1)
    repeat_shape = list(idx.shape)
    repeat_shape[0] = 1
    batch_indices = torch.arange(B, dtype=torch.long).to(device).view(view_shape).repeat(repeat_shape)
    new_points = points[batch_indices, idx, :]
    return new_points

# fathest sampling to ensure good coverage; Note: modelnet dataloader also use this function
def farthest_point_sample(xyz, npoint):
    """
    Input:
        xyz: pointcloud data, [B, N, 3]
        npoint: number of samples
    Return:
        centroids: sampled pointcloud index, [B, npoint]
    """
    device = xyz.device
    B, N, C = xyz.shape
    centroids = torch.zeros(B, npoint, dtype=torch.long).to(device)
    distance = torch.ones(B, N).to(device) * 1e10
    farthest = torch.randint(0, N, (B,), dtype=torch.long).to(device)
    batch_indices = torch.arange(B, dtype=torch.long).to(device)
    for i in range(npoint):
        centroids[:, i] = farthest
        centroid = xyz[batch_indices, farthest, :].view(B, 1, 3)
        dist = torch.sum((xyz - centroid) ** 2, -1)
        mask = dist < distance
        distance[mask] = dist[mask]
        farthest = torch.max(distance, -1)[1]
    return centroids


def query_ball_point(radius, nsample, xyz, new_xyz):
    """
    Input:
        radius: local region radius
        nsample: max sample number in local region
        xyz: all points, [B, N, 3]
        new_xyz: query points, [B, S, 3]
    Return:
        group_idx: grouped points index, [B, S, nsample]
    """
    device = xyz.device
    B, N, C = xyz.shape
    _, S, _ = new_xyz.shape
    group_idx = torch.arange(N, dtype=torch.long).to(device).view(1, 1, N).repeat([B, S, 1]) # BxSxN
    sqrdists = square_distance(new_xyz, xyz) # BxSxN

    # replace the values in the group_idx which is bigger than radius^2 w. N
    group_idx[sqrdists > radius ** 2] = N # (B,S,N) those bigger, assign idx w. lgest index(i.e. N)

    # torch's sort method return A namedtuple of (values, indices)
    group_idx = group_idx.sort(dim=-1)[0][:, :, :nsample] # (B,S,32), only retrieve pts w. sm dist.

    # Aha moment, those nearest nsample(32) points idx might be like [1,9,11,12,N,N] 
    # how to handle NN? just replace the N w. the nearest id
    group_first = group_idx[:, :, 0].view(B, S, 1).repeat([1, 1, nsample])
    mask = group_idx == N #
    group_idx[mask] = group_first[mask]
    
    return group_idx # (B,S,32)


def sample_and_group(npoint, radius, nsample, xyz, points, returnfps=False):
    """
    Input:
        npoint: the number of sampled pts, denote by S
        radius: search radius for ball query
        nsample: max sample number in local region
        xyz: input points position data, [B, N, 3]
        points: input points data, [B, N, D]
        returnfps: default False, whether return FPS relevant variables, e.g. fps_idx, etc.
    Return:
        new_xyz: sampled points position data, [B, npoint, nsample, 3]
        new_points: sampled points data, [B, npoint, nsample, 3+D]
    """
    # obtain sampled pts using FPS (calling fathest_point_sample method)
    B, N, C = xyz.shape
    S = npoint
    fps_idx = farthest_point_sample(xyz, npoint) # [B,S]
    torch.cuda.empty_cache()
    new_xyz = index_points(xyz, fps_idx) # (B,S,C)  (C=3)
    
    # obtain each pt's ball query pts of new_xyz.
    torch.cuda.empty_cache()
    idx = query_ball_point(radius, nsample, xyz, new_xyz)  # (B,S,nsample)
    torch.cuda.empty_cache()
    grouped_xyz = index_points(xyz, idx) # (B, S, nsample, C)
    
    torch.cuda.empty_cache()
    # normalize each partition
    grouped_xyz_norm = grouped_xyz - new_xyz.view(B, S, 1, C) # (B, S, nsample, C) 
    torch.cuda.empty_cache()

    # if existing data features for each pt, then concat w. normalized xyz coordinates
    if points is not None:
        grouped_points = index_points(points, idx)
        new_points = torch.cat([grouped_xyz_norm, grouped_points], dim=-1) # [B, npoint, nsample, C+D]
    else:
        new_points = grouped_xyz_norm
    if returnfps:
        return new_xyz, new_points, grouped_xyz, fps_idx
    else:
        return new_xyz, new_points # (B,S,C) (B,S,nsample,C+D)


def sample_and_group_all(xyz, points):
    """ similar to sample_and_group method, but this method assume only 1 sampled pt and N as ball query('s K parameter)
        will be used for classification
    Input:
        xyz: input points position data, [B, N, 3]
        points: input points data, [B, N, D]
    Return:
        new_xyz: sampled points position data, [B, 1, 3]
        new_points: sampled points data, [B, 1, N, 3+D]
    """
    device = xyz.device
    B, N, C = xyz.shape
    new_xyz = torch.zeros(B, 1, C).to(device)
    grouped_xyz = xyz.view(B, 1, N, C)
    if points is not None:
        new_points = torch.cat([grouped_xyz, points.view(B, 1, N, -1)], dim=-1)
    else:
        new_points = grouped_xyz
    return new_xyz, new_points # (B,1,3) (B,1,N,3+D)

"""
correspond set abstraction module of the achitecture
- Intuitively, pointnet++ learn features locally and hierarchically (unlike pointnet which learn either global or individually)
- Essentially, it partition the input PC into several clusters, then apply pointnet vanilla to aggregate features
- it will do 2 things: 
  - 1)partition the input PC into several clusters (i.e. farthest sampling and grouping by KNN/ball query),
  - 2)learn locally using pointnet vanilla
"""
class PointNetSetAbstraction(nn.Module):
    def __init__(self, npoint, radius, nsample, in_channel, mlp, group_all):
        """

        Args:
            npoint ([int]): the number of sampled pts, e.g. 1024
            radius ([float]): the search radius of ball query for each sampled pt, e.g. 0.2
            nsample ([int]): max sample number in local region, e.g. 32
            in_channel ([int]): input channel, e.g. 9+3
            mlp ([list]): PointNet vanilla MLP output channels, e.g. [64,128,256]
            group_all ([bool]): for classification use, aggregate over all points(i.e. only 1 pt and N nearest nb pts)
        """
        super(PointNetSetAbstraction, self).__init__()
        self.npoint = npoint
        self.radius = radius
        self.nsample = nsample
        self.mlp_convs = nn.ModuleList()
        self.mlp_bns = nn.ModuleList()
        last_channel = in_channel
        for out_channel in mlp:
            self.mlp_convs.append(nn.Conv2d(last_channel, out_channel, 1))
            self.mlp_bns.append(nn.BatchNorm2d(out_channel))
            last_channel = out_channel
        self.group_all = group_all

    def forward(self, xyz, points):
        """
        Input:
            xyz: input points position data, [B, C, N]
            points: input points data, [B, D, N]
        Return:
            new_xyz: sampled points position data, [B, C, S]
            new_points_concat: sample points feature data, [B, D', S]
        """
        xyz = xyz.permute(0, 2, 1)
        if points is not None:
            points = points.permute(0, 2, 1)

        if self.group_all: # only use when for cls task
            new_xyz, new_points = sample_and_group_all(xyz, points)
        else:
            # (B,S,C)  (B,S,K,C)   K=nsample
            # new_xyz: sampled points position data, [B, npoint, C]
            # new_points: sampled points data, [B, npoint, nsample, C+D]
            new_xyz, new_points = sample_and_group(self.npoint, self.radius, self.nsample, xyz, points)
            
        new_points = new_points.permute(0, 3, 2, 1) # (B, C+D, K,S)
        for i, conv in enumerate(self.mlp_convs):
            bn = self.mlp_bns[i]
            new_points =  F.relu(bn(conv(new_points))) # # (B,mlp[-1],K,S), conv2d and bn2d, different from pointnet but the essence is the same
        
        # max pooling along K's dim
        new_points = torch.max(new_points, 2)[0] # (B,mlp[-1],S) e.g. 6x64x1024
        new_xyz = new_xyz.permute(0, 2, 1) ## (B,C,S) e.g. 6x3x64
        return new_xyz, new_points # (B,C,S) (B,mlp[-1],S) e.g. 6x64x1024


class PointNetSetAbstractionMsg(nn.Module):
    def __init__(self, npoint, radius_list, nsample_list, in_channel, mlp_list):
        super(PointNetSetAbstractionMsg, self).__init__()
        self.npoint = npoint
        self.radius_list = radius_list
        self.nsample_list = nsample_list
        self.conv_blocks = nn.ModuleList()
        self.bn_blocks = nn.ModuleList()
        for i in range(len(mlp_list)):
            convs = nn.ModuleList()
            bns = nn.ModuleList()
            last_channel = in_channel + 3
            for out_channel in mlp_list[i]:
                convs.append(nn.Conv2d(last_channel, out_channel, 1))
                bns.append(nn.BatchNorm2d(out_channel))
                last_channel = out_channel
            self.conv_blocks.append(convs)
            self.bn_blocks.append(bns)

    def forward(self, xyz, points):
        """
        Input:
            xyz: input points position data, [B, C, N]
            points: input points data, [B, D, N]
        Return:
            new_xyz: sampled points position data, [B, C, S]
            new_points_concat: sample points feature data, [B, D', S]
        """
        xyz = xyz.permute(0, 2, 1)
        if points is not None:
            points = points.permute(0, 2, 1)

        B, N, C = xyz.shape
        S = self.npoint
        new_xyz = index_points(xyz, farthest_point_sample(xyz, S))
        new_points_list = []
        for i, radius in enumerate(self.radius_list):
            K = self.nsample_list[i]
            group_idx = query_ball_point(radius, K, xyz, new_xyz)
            grouped_xyz = index_points(xyz, group_idx)
            grouped_xyz -= new_xyz.view(B, S, 1, C)
            if points is not None:
                grouped_points = index_points(points, group_idx)
                grouped_points = torch.cat([grouped_points, grouped_xyz], dim=-1)
            else:
                grouped_points = grouped_xyz

            grouped_points = grouped_points.permute(0, 3, 2, 1)  # [B, D, K, S]
            for j in range(len(self.conv_blocks[i])):
                conv = self.conv_blocks[i][j]
                bn = self.bn_blocks[i][j]
                grouped_points =  F.relu(bn(conv(grouped_points)))
            new_points = torch.max(grouped_points, 2)[0]  # [B, D', S]
            new_points_list.append(new_points)

        new_xyz = new_xyz.permute(0, 2, 1)
        new_points_concat = torch.cat(new_points_list, dim=1)
        return new_xyz, new_points_concat


class PointNetFeaturePropagation(nn.Module):
    def __init__(self, in_channel, mlp):
        super(PointNetFeaturePropagation, self).__init__()
        self.mlp_convs = nn.ModuleList()
        self.mlp_bns = nn.ModuleList()
        last_channel = in_channel
        for out_channel in mlp:
            self.mlp_convs.append(nn.Conv1d(last_channel, out_channel, 1))
            self.mlp_bns.append(nn.BatchNorm1d(out_channel))
            last_channel = out_channel

    def forward(self, xyz1, xyz2, points1, points2):
        """ interpolation then conat previous layer's features to recover local-level features followed by MLPs
        Input:
            xyz1: input points position data, [B, C, N]
            xyz2: sampled input points position data, [B, C, S]
            points1: input points data, [B, D, N]
            points2: input points data, [B, D, S]
        Return:
            new_points: upsampled points data, [B, D', N]
        """
        xyz1 = xyz1.permute(0, 2, 1) # BxNxC
        xyz2 = xyz2.permute(0, 2, 1) # BxSxC

        points2 = points2.permute(0, 2, 1) # BxSxD
        B, N, C = xyz1.shape
        _, S, _ = xyz2.shape

        if S == 1:
            interpolated_points = points2.repeat(1, N, 1) # BxNxD
        else:
            dists = square_distance(xyz1, xyz2) # (B,N,S) each pt in xyz1 has S number of distance
            dists, idx = dists.sort(dim=-1) # torch's sort method
            dists, idx = dists[:, :, :3], idx[:, :, :3]  # [B, N, 3] only consider 3 nearest elements of each pt in xyz1

            # inverse distance weighted interpolation
            dist_recip = 1.0 / (dists + 1e-8) # BxNx3
            norm = torch.sum(dist_recip, dim=2, keepdim=True) # BxNx1
            weight = dist_recip / norm # BxNx3
            # gain points features: index_points(points2,idx) (B,N,3,D)
            # weights (B,N,3,1) 
            interpolated_points = torch.sum(index_points(points2, idx) * weight.view(B, N, 3, 1), dim=2) # (B,N,D1)

        if points1 is not None:
            points1 = points1.permute(0, 2, 1 ) # BxNxD12, e.g. BxNx256
            new_points = torch.cat([points1, interpolated_points], dim=-1) # BxNx2D, skip connection
        else:
            new_points = interpolated_points

        new_points = new_points.permute(0, 2, 1) # Bx(D1+D2)xN
        for i, conv in enumerate(self.mlp_convs):
            bn = self.mlp_bns[i]
            new_points = F.relu(bn(conv(new_points))) # BX mlp[-1]xN
        return new_points

