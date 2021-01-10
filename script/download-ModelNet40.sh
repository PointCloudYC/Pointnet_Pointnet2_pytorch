#！/bin/sh
DATA_DIR="data"
DATASET_URL="https://shapenet.cs.stanford.edu/media/modelnet40_normal_resampled.zip"
DATASET_ORIGINAL_NAME="modelnet40_normal_resampled"
DATASET_NAME="ModelNet40"

# option 1: download directly to your project folder
cd ..
mkdir $DATA_DIR && cd $DATA_DIR
wget $DATASET_URL --no-check-certificate

unzip "$DATASET_ORIGINAL_NAME.zip" && mv "$DATASET_ORIGINAL_NAME" "$DATASET_NAME"
rm "$DATASET_ORIGINAL_NAME.zip"

# option 2: download data in one dir(e.g. xxx/dataset/ModelNet) and then create a soft link in the current project data folder
# same as above to download the data
# ln -s /media/yinchao/Mastery/dataset/ModelNet40 ./data/ModelNet40