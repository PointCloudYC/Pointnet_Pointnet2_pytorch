#！/bin/sh
DATA_DIR="data"
DATASET_URL="https://shapenet.cs.stanford.edu/ericyi/shapenetcore_partanno_segmentation_benchmark_v0.zip"
DATASET_ORIGINAL_NAME="shapenetcore_partanno_segmentation_benchmark_v0"
DATASET_NAME="ShapeNet"

# option 1: download directly to your project folder
cd ..
mkdir $DATA_DIR && cd $DATA_DIR
wget $DATASET_URL --no-check-certificate

unzip "$DATASET_ORIGINAL_NAME.zip" && mv "$DATASET_ORIGINAL_NAME" "$DATASET_NAME"
rm "$DATASET_ORIGINAL_NAME.zip"

# option 2: download data in one dir(e.g. xxx/dataset/ShapeNet) and then create a soft link in the current project data folder
# same as above to download the data
# ln -s /media/yinchao/Mastery/dataset/ShapeNet ./data/ShapeNet