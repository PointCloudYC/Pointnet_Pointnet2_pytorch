#！/bin/sh
DATA_DIR="S3DIS"
DATASET_URL="https://shapenet.cs.stanford.edu/media/indoor3d_sem_seg_hdf5_data.zip"
DATASET_ORIGINAL_NAME="indoor3d_sem_seg_hdf5_data.zip"
DATASET_NAME="S3DIS"

# option 1: download directly to your project folder
cd ..
mkdir $DATA_DIR && cd $DATA_DIR
wget $DATASET_URL --no-check-certificate

unzip "$DATASET_ORIGINAL_NAME.zip"
# rm "$DATASET_ORIGINAL_NAME.zip"

# option 2: download data in one dir(e.g. xxx/dataset/ShapeNet) and then create a soft link in the current project data folder
# same as above to download the data
