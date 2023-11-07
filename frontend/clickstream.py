"""
Created on 2023-06-11

@author: wf
"""
from tqdm import tqdm
from dataclasses import dataclass
from datetime import datetime
import glob
import json
import os
import traceback
from typing import Any, Dict, List, Optional
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%b %d, %Y %I:%M:%S %p")

@dataclass
class PageHit:
    path: str
    timeStamp: datetime

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PageHit":
        data["timeStamp"] = parse_date(data["timeStamp"])
        return PageHit(**data)

@dataclass
class UserAgent:
    hasSyntaxError: bool
    hasAmbiguity: bool
    ambiguityCount: int
    userAgentString: str
    debug: bool
    allFields: Dict[str, Dict[str, Any]]
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "UserAgent":
        allFields = data.get("allFields", {})
    
        # Use `.get()` with defaults to prevent KeyError
        return UserAgent(
            hasSyntaxError=data.get("hasSyntaxError", False),
            hasAmbiguity=data.get("hasAmbiguity", False),
            ambiguityCount=data.get("ambiguityCount", 0),
            userAgentString=data.get("userAgentString", ""),
            debug=data.get("debug", False),
            allFields=allFields
        )

@dataclass
class ClickStream:
    url: str
    ip: str
    domain: str
    timeStamp: datetime
    pageHits: List[PageHit]
    userAgent: UserAgent
    userAgentHeader: Optional[str]= None
    referrer: Optional[str] = None
    acceptLanguage: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ClickStream":
        data["timeStamp"] = parse_date(data["timeStamp"])
        # Ensure `pageHits` are processed into PageHit instances
        data["pageHits"] = [PageHit.from_dict(hit) for hit in data.get("pageHits", [])]
        # Remove any keys from `data` that are not fields of the `ClickStream` dataclass
        #data = {key: value for key, value in data.items() if key in ClickStream.__annotations__}

        # Let the `_postprocess` handle the userAgent conversion
        data = ClickStream._postprocess(data)
        return ClickStream(**data)
    
    @staticmethod
    def _postprocess(data: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure `userAgent` is a dictionary before trying to convert
        if isinstance(data.get("userAgent"), dict):
            data["userAgent"] = UserAgent.from_dict(data["userAgent"])
        # If `pageHits` needs to be processed again (not typically necessary if handled in `from_dict`)
        if isinstance(data.get("pageHits"), list):
            data["pageHits"] = [PageHit.from_dict(hit) if isinstance(hit, dict) else hit for hit in data["pageHits"]]
        return data

@dataclass
class ClickstreamLog:
    """
    single log of clickstreams
    """
    debug: bool
    MAX_CLICKSTREAMS: int
    LOGGING_TIME_PERIOD: int
    MAX_SESSION_TIME: int
    FLUSH_PERIOD: int
    startTime: datetime
    lastFlush: datetime
    lastLogRotate: datetime
    fileName: str
    clickStreams: List[ClickStream]

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%b %d, %Y %I:%M:%S %p")

    @classmethod
    def from_json(cls, json_file: str):
        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            
        # Handle nested structures
        data = ClickstreamLog._postprocess(data)

        return ClickstreamLog(**data)
    
    @classmethod
    def _postprocess(cls,data: Dict[str, Any]) -> Dict[str, Any]:
        data["startTime"] = cls._parse_date(data["startTime"])
        data["lastFlush"] = cls._parse_date(data["lastFlush"])
        data["lastLogRotate"] =cls._parse_date(data["lastLogRotate"])
        data["clickStreams"] = [ClickStream.from_dict(cs) for cs in data.get("clickStreams", [])]
        return data

class ClickstreamManager(object):
    """
    logging of client clicks
    """

    def __init__(self, root_path: str):
        """
        Constructor
        """
        self.root_path = root_path
        self.clickstream_logs: List[ClickstreamLog] = []
        
    def load_clickstream_logs(self,limit: Optional[int] = None,show_progress:bool=True) -> None:
        '''
        Load all clickstream logs from the directory
        '''
        # Find all json files in the directory
        json_files = glob.glob(os.path.join(self.root_path, '*.json'))
        # If a limit is set, truncate the file list
        if limit is not None:
            json_files = json_files[:limit]
            
        # Prepare tqdm iterator if required and tqdm is available
        iterator = tqdm(json_files, desc="Loading Clickstream Logs") if show_progress else json_files

        # Load each file
        
        for json_file in iterator:
            try:
                # Parse the JSON file into ClickstreamLog
                clickstream_log = ClickstreamLog.from_json(json_file)
                self.clickstream_logs.append(clickstream_log)
            except json.JSONDecodeError as jde:
                # Handle JSON-specific parsing errors
                print(f"JSON decode error in file {json_file}: {jde.msg}")
                print(f"Error at line {jde.lineno}, column {jde.colno}")    
            except Exception as e:
                tb = traceback.format_exc()  # This will give you the stack trace
                print(f"Error loading {json_file}: {e}")
                print(tb)  # Print stack trace to get more details about the exception

    def export_to_rdf(self, rdf_file: str, rdf_namespace: str, rdf_format: str = "turtle", verbose: bool = True) -> None:
        """
        Export clickstream logs to an RDF file in the specified format.
        :param rdf_file: The file to write the RDF data to.
        :param rdf_namespace: The base namespace URI for the RDF export.
        :param rdf_format: The RDF serialization format to use (default is "turtle").
        :param verbose: If True, print the output message.
        """
        # Namespace definition
        CS = Namespace(rdf_namespace)

        # Initialize the graph
        g = Graph()
        g.bind("cs", CS)

        # Counter for unique IDs
        entity_counter = 1

        # Iterate through clickstream logs and convert to RDF
        for log in self.clickstream_logs:
            for stream in log.clickStreams:
                # Create a URI for each ClickStream record with a unique ID
                stream_uri = URIRef(f"{rdf_namespace}clickstream/{entity_counter}")
                entity_counter += 1
                
                # Add properties to the stream URI
                g.add((stream_uri, RDF.type, CS.ClickStream))
                g.add((stream_uri, CS.url, Literal(stream.url)))
                g.add((stream_uri, CS.ip, Literal(stream.ip)))
                g.add((stream_uri, CS.domain, Literal(stream.domain)))
                g.add((stream_uri, CS.userAgentHeader, Literal(stream.userAgentHeader)))
                g.add((stream_uri, CS.timeStamp, Literal(stream.timeStamp.isoformat(), datatype=XSD.dateTime)))
                
                # Optional referrer information
                if stream.referrer:
                    g.add((stream_uri, CS.referrer, Literal(stream.referrer)))

                # User Agent details
                ua_uri = URIRef(f"{rdf_namespace}useragent/{entity_counter}")
                entity_counter += 1
                g.add((ua_uri, RDF.type, CS.UserAgent))
                g.add((ua_uri, CS.hasSyntaxError, Literal(stream.userAgent.hasSyntaxError)))
                g.add((ua_uri, CS.hasAmbiguity, Literal(stream.userAgent.hasAmbiguity)))
                g.add((ua_uri, CS.ambiguityCount, Literal(stream.userAgent.ambiguityCount)))
                g.add((ua_uri, CS.userAgentString, Literal(stream.userAgent.userAgentString)))
                g.add((stream_uri, CS.userAgent, ua_uri))

                # Page Hits
                for hit in stream.pageHits:
                    hit_uri = URIRef(f"{rdf_namespace}pagehit/{entity_counter}")
                    entity_counter += 1
                    g.add((hit_uri, RDF.type, CS.PageHit))
                    g.add((hit_uri, CS.path, Literal(hit.path)))
                    g.add((hit_uri, CS.timeStamp, Literal(hit.timeStamp.isoformat(), datatype=XSD.dateTime)))
                    g.add((stream_uri, CS.pageHits, hit_uri))

        # Serialize and save to file
        g.serialize(destination=rdf_file, format=rdf_format)
        
        if verbose:
            print(f"Exported RDF to {rdf_file}")
