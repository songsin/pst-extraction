from pyspark import SparkContext, SparkConf

import sys, os
import json
import argparse
import datetime

from functools import partial
from filters import valid_json_filter

def fn_to_doc(line):
    try:
        doc = {}
        data = json.loads(line)
        doc['data'] = data
        return [json.dumps(doc)]
    except:
        return []

if __name__ == "__main__":

    desc='elastic search ingest'
    parser = argparse.ArgumentParser(
        description=desc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=desc)

    parser.add_argument("input_path", help="lines of json to ingest")
    parser.add_argument("es_resource", help="index and doc_type (my-index/doc)")    
    parser.add_argument("--id_field", help="id field to map into es")    
    parser.add_argument("--es_nodes", default="127.0.0.1:9200", help="es.nodes")
    parser.add_argument("-v", "--validate_json", action="store_true", help="Filter broken json.  Test each json object and output broken objects to tmp/failed.")

    args = parser.parse_args()

    print "NODES:"+str(args.es_nodes)
    conf = SparkConf().setAppName("Elastic Ingest")
    sc = SparkContext(conf=conf)

    lex_date = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    print "Running with json filter {}.".format("enabled" if args.validate_json else "disabled")
    filter_fn = partial(valid_json_filter, os.path.basename(__file__), lex_date, not args.validate_json)


    es_write_conf = {
        "es.nodes" : args.es_nodes,
        "es.resource" : args.es_resource,
        #"es.nodes.client.only" : "true",
        "es.input.json" : "yes"
    }
    
    if args.id_field:
      es_write_conf["es.mapping.id"] = args.id_field

    hdfs_path = args.input_path
    d = sc.textFile(hdfs_path).filter(filter_fn).map(lambda x : ("key", x))

    d.saveAsNewAPIHadoopFile(
        path='-', 
        outputFormatClass="org.elasticsearch.hadoop.mr.EsOutputFormat",
        keyClass="org.apache.hadoop.io.NullWritable",
        valueClass="org.apache.hadoop.io.Text",
        #valueClass="org.elasticsearch.hadoop.mr.LinkedMapWritable", 
        conf=es_write_conf)

