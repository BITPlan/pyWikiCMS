#!/bin/bash
#WF 2023-11-07

# Set the path for the clickstream data and properties file
CLICKSTREAM_DATA_DIR="$HOME/.clickstream"
CLICKSTREAM_DATA_FILE="clicks_2023-11-06.ttl"
RWSTORE_PROPERTIES_FILE="RWStore.properties"
BLAZEGRAPH_CONTAINER_NAME="blazegraph"
BLAZEGRAPH_IMAGE="lyrasis/blazegraph:2.1.5"
BLAZEGRAPH_PORT=8889

echo "$CLICKSTREAM_DATA_FILE to $BLAZEGRAPH_CONTAINER_NAME docker container ..."
# Stop and remove any existing Blazegraph container with the same name
docker stop blazegraph &>/dev/null
docker rm blazegraph &>/dev/null


# Check if the clickstream data file and properties file exist
if [ ! -f "$CLICKSTREAM_DATA_DIR/$CLICKSTREAM_DATA_FILE" ]; then
    echo "Clickstream data file not found at $CLICKSTREAM_DATA_DIR/$CLICKSTREAM_DATA_FILE"
    exit 1
fi

if [ ! -f "$CLICKSTREAM_DATA_DIR/$RWSTORE_PROPERTIES_FILE" ]; then
    echo "RWStore properties file not found at $CLICKSTREAM_DATA_DIR/$RWSTORE_PROPERTIES_FILE"
    url="https://raw.githubusercontent.com/cmungall/sparqlprog/master/examples/RWStore.properties"
    echo "downloading from $url"
    cd $CLICKSTREAM_DATA_DIR
    wget $url
fi

# Run the Blazegraph container with the volume mount
docker run --name $BLAZEGRAPH_CONTAINER_NAME -d \
  -p $BLAZEGRAPH_PORT:8080 \
  -v $CLICKSTREAM_DATA_DIR:/data \
  $BLAZEGRAPH_IMAGE

if [ $? -ne 0 ]; then
    echo "Failed to start the Blazegraph container"
    exit 1
fi

# Check for Blazegraph startup message
echo "Waiting for Blazegraph to start..."
STARTUP_COMPLETE_MESSAGE="Started @"  # message part that indicates Blazegraph is ready
for i in {1..30}; do
    if docker logs $BLAZEGRAPH_CONTAINER_NAME 2>&1 | grep "$STARTUP_COMPLETE_MESSAGE" > /dev/null; then
        echo "Blazegraph started successfully."
        break
    fi
    echo "Still waiting for Blazegraph to start..."
    sleep 1
done

# Prepare the data loading configuration
DATA_LOADER_FILE="$CLICKSTREAM_DATA_DIR/dataloader.txt"
cat << EOF > $DATA_LOADER_FILE
quiet=false
verbose=0
closure=false
dumpto=/data/outputfile.nq.gz

propertyFile=/data/$RWSTORE_PROPERTIES_FILE
defaultGraph=https://example.org/blazegraph/namespace
fileOrDirs=/data/$CLICKSTREAM_DATA_FILE
format=turtle
EOF

# Trigger the data load
echo "Loading data into Blazegraph..."
curl -X POST \
  --data-binary @$DATA_LOADER_FILE \
  --header 'Content-Type:text/plain' \
  http://localhost:$BLAZEGRAPH_PORT/bigdata/dataloader

# Check the response of the curl command
if [ $? -ne 0 ]; then
    echo "Data load request failed"
    exit 1
fi

# Clean up the data loader file if not needed anymore
rm $DATA_LOADER_FILE

echo "Data load process initiated. Check logs for details."
