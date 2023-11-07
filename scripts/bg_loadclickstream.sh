#!/bin/bash
#WF 2023-11-07

# Set the path for the clickstream data and properties file
CLICKSTREAM_DATA_DIR="$HOME/.clickstream"
CLICKSTREAM_RDFPREFIX="clicks_2023-11-07_part"
RWSTORE_PROPERTIES_FILE="RWStore.properties"
BLAZEGRAPH_CONTAINER_NAME="blazegraph"
BLAZEGRAPH_IMAGE="lyrasis/blazegraph:2.1.5"
BLAZEGRAPH_PORT=8889
BLAZEGRAPH_URL="http://localhost:$BLAZEGRAPH_PORT/bigdata"

function count_triples() {
    # SPARQL query to count triples
    QUERY_STRING="SELECT (COUNT(*) as ?triples) WHERE { ?s ?p ?o . }"

    # URL encode the query string
    ENCODED_QUERY=$(python -c "import urllib.parse; print(urllib.parse.quote('''$QUERY_STRING'''))")

    # Perform the query
    RESPONSE=$(curl -s -X GET --header 'Accept: application/sparql-results+json' \
      "${BLAZEGRAPH_URL}/sparql?query=${ENCODED_QUERY}")

    # Extract the number of triples from the JSON response
    TRIPLE_COUNT=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['results']['bindings'][0]['triples']['value'])")

    echo "Total number of triples: $TRIPLE_COUNT"
}

# Check for the '--count' flag
if [[ " $@ " =~ " --count " ]]; then
    count_triples
    exit 0
fi

function start_blazegraph() {
   # Stop and remove any existing Blazegraph container with the same name
   echo "stopping $BLAZEGRAPH_CONTAINER_NAME"
   docker stop $BLAZEGRAPH_CONTAINER_NAME
   echo "removing $BLAZEGRAPH_CONTAINER_NAME"
   docker rm $BLAZEGRAPH_CONTAINER_NAME

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
}

#
# load a single file
#
function load_data() {
    local file_to_load=$1
    echo "Loading $file_to_load into Blazegraph..."

    DATA_LOADER_FILE="$CLICKSTREAM_DATA_DIR/dataloader.txt"
    cat << EOF > $DATA_LOADER_FILE
quiet=false
verbose=0
closure=false
dumpto=/data/outputfile.nq.gz

propertyFile=/data/$RWSTORE_PROPERTIES_FILE
defaultGraph=https://example.org/blazegraph/namespace
fileOrDirs=/data/$file_to_load
format=turtle
EOF

    # Trigger the data load for the current file
    curl -X POST \
      --data-binary @$DATA_LOADER_FILE \
      --header 'Content-Type:text/plain' \
      "$BLAZEGRAPH_URL"/dataloader

    # Check the response of the curl command
    if [ $? -ne 0 ]; then
        echo "Data load request failed for $file_to_load"
        exit 1
    else
        echo "Data loaded for $file_to_load"
    fi

    # Clean up the data loader file if not needed anymore
    rm $DATA_LOADER_FILE
}

if [ ! -f "$CLICKSTREAM_DATA_DIR/$RWSTORE_PROPERTIES_FILE" ]; then
    echo "RWStore properties file not found at $CLICKSTREAM_DATA_DIR/$RWSTORE_PROPERTIES_FILE"
    url="https://raw.githubusercontent.com/cmungall/sparqlprog/master/examples/RWStore.properties"
    echo "downloading from $url"
    cd $CLICKSTREAM_DATA_DIR
    wget $url
fi

echo "importing $CLICKSTREAM_RDFPREFIX files to blazegraph "
start_blazegraph

# Iterate over the batch files and call the load_data function for each one
for batch_file in "$CLICKSTREAM_DATA_DIR/$CLICKSTREAM_RDFPREFIX"*.nt
do
    load_data "$(basename "$batch_file")"
done
