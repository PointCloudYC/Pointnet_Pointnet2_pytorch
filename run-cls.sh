#!/bin/sh

# prepare modelnet40

# train; note: u can choose other models, e.g. pointnet2_cls_msg
# however, my pc can not run MSG model due to out-of-memory error of CUDA
python train_cls.py \
--model pointnet2_cls_ssg \
--normal \
--log_dir pointnet2_cls_ssg \
--batch_size 24 \
--epoch 200

python test_cls.py 
--normal \
--log_dir pointnet2_cls_ssg


# run a script 60min later
# sleep 60m && ./run.sh