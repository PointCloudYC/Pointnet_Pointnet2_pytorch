#!/bin/sh

# prepare s3dis
# cd data_utils
# python collect_indoor3d_data.py

# train
python train_semseg.py \
--model pointnet2_sem_seg \
--test_area 5 \
--log_dir pointnet2_sem_seg


# test
python test_semseg.py \
--log_dir pointnet2_sem_seg \
--test_area 5 \
--visual
