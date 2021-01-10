#!/bin/sh
# s3dis
# cd data_utils
# python collect_indoor3d_data.py
python train_semseg.py --model pointnet2_sem_seg --test_area 5 --log_dir pointnet2_sem_seg
python test_semseg.py --log_dir pointnet2_sem_seg --test_area 5 --visual

# modelnet40
python train_cls.py --model pointnet2_cls_ssg --normal --log_dir pointnet2_cls_ssg --batch_size 24 --epoch 200
python test_cls.py --normal --log_dir pointnet2_cls_ssg
# can not run MSG model since out-of-memory error of CUDA
# python train_cls.py --model pointnet2_cls_msg --normal --log_dir pointnet2_cls_msg


# run a script 60min later
# sleep 60m && ./run.sh