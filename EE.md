 TOC]

# time
- 30min, Jan 6th, 2021
- run, code analysis, and comment, 3h30min, Jan 10,2021


# explore
## code structure(key files are in bold)

- data_utils, ModelNet, ShapeNet and S3DIS dataset and pipelines to load the data
  --collect_indoor3d_data.py, generate a npy with XYZRGBL format for each room(272 rooms) (sim. code to original code)
  --indoor3d_util.py, generate partitions(i.e. 1x1m blocks for each room), will be called by S3DISDataloader file (sim. code to original code)
  --**S3DISDataLoader.py**, declare pytorch Dataset object with init and _get_item methods; in _get_item method, generate a collection NxD examples, in particular, each room will be used to create round(room_count/4096)*sample_rate blocks(where sample_rate by default is 1), each block is generated by randomly choose 1 pt as the center, then get a 1mx1m block. (Note: such sampling strategy is different from original paper which partition each room with strides ending up generating different h5 files).
  --ModelNetDataLoader.py, declare pytorch Dataset object with init and_get_item methods; in _get_item method, generate a collection of NxD examples by select 1024 points from 1 PC.
  --ShapeNetDataLoader.py, simlar, but for ShapeNet dataset

- models, all kinds of models for cls, part seg, and sem seg.
  --pointnet.py, STN3d, STNkd for T-Net moduel and PointNetEncoder for extract global feature for PCs.
  --pointnet_cls.py, PointNet cls network
  --pointnet_part_seg.py,PointNet part seg network
  --pointnet_sem_seg.py, PointNet sem seg network
  --**pointnet_util.py**, utility file, focus on PointNetFeaturePropagation, PointNetSetAbstraction[Msg], sampling relevant methods.
  --pointnet2_cls_msg.py
  --pointnet2_cls_ssg.py
  --pointnet2_part_seg_msg.py
  --pointnet2_part_seg_ssg.py
  --**pointnet2_sem_seg.py**, PointNet++ SSG model where two special operations including Abstraction and FeaturePropagation
  --**pointnet2_sem_seg_msg.py**, PointNet++ MSG model where two special operations including AbstractionMsg and FeaturePropagation

- visualizer, visualize the data
- provider.py, utility code

- train_x.py, test_x.py, where x denotes {cls,partseg,semseg}
  --train_semseg.py, 1)load user arguments, set up logs, etc, 2)create dataset and dataloader objects for train and test set, 3)train and evaluate ,4) serialize models every 5 epoch and save best models.

### training and evaluate

**train_classification.py, train_segmentation.py**

- train cls model; train_cls.py as the main file
- train seg model; train_semseg.py as the main file

## run code

### classification model(ModelNet40)

- download data; download data to a local folder, then make a soft link to data under current project. (check scripts/download-xx.sh) 
- run code; `python train_cls.py --model pointnet2_cls_ssg --normal --log_dir pointnet2_cls_ssg`
 - can not run the msg model since CUDA OOM error.(out-of-memory error); when set batch size to 16, still in vain; as a result, we use the ssg model; set batch size to 8, might work


### semantic segmentation model(S3DIS)

- download data; download data to a local folder, then make a soft link to data under current project. (check scripts/download-xx.sh) 
- preprocess the raw data; `python collect_indoor3d_data.py`, the generated output dir is `stanford_indoor3d`
  - 272 rooms; `find *.npy | wc -l`
- run code; `python train_semseg.py --model pointnet2_sem_seg --test_area 5 --log_dir pointnet2_sem_seg` (check run.sh); for a new experiment, remember to assign a new log_dir
  - very slow to run the model, ~1 hour/epoch on S3DIS (7 hour only 7 epochs on the S3DIS dataset);
  - after 7 epochs, the eval metrics are 0.508， 0.809 for mIoU and OA respectively
  - log files in log/sem_seg/xx

# exploitation

## how to prepare the blocks?

- In orginal pointnet repo, it partition the point cloud into blocks 1mx1m with stride 0.5m, then each block will sample fixed pts(4096)

- In this repo, generate a collection of NxD examples, in particular, each room will be used to create round(room_count/4096)*sample_rate blocks (where sample_rate by default is 1); details check S3DISDataLoader.py

## run the code on PSNet?