"""
Created on 2023-06-11

@author: wf
"""
import glob
import json
import os
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD
from tqdm import tqdm


class DateParse:
    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """Parse a string to a datetime object.

        Args:
            date_str (str): The date string to parse.

        Returns:
            datetime: The parsed datetime object.
        """
        return datetime.strptime(date_str, "%b %d, %Y %I:%M:%S %p")


@dataclass
class PageHit:
    """Represents a single page hit with path and timestamp."""

    path: str
    timeStamp: datetime

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PageHit":
        data["timeStamp"] = DateParse.parse_date(data["timeStamp"])
        return PageHit(**data)


@dataclass
class UserAgent:
    """Represents a user agent with syntax errors, ambiguity and other attributes."""

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
            allFields=allFields,
        )


@dataclass
class ClickStream:
    """Represents a clickstream with associated page hits and user agent data."""

    url: str
    ip: str
    domain: str
    timeStamp: datetime
    pageHits: List[PageHit]
    userAgent: UserAgent
    userAgentHeader: Optional[str] = None
    referrer: Optional[str] = None
    acceptLanguage: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ClickStream":
        data["timeStamp"] = DateParse.parse_date(data["timeStamp"])
        # Ensure `pageHits` are processed into PageHit instances
        # Initialize an empty list to store PageHit instances.
        page_hits = []

        # Iterate through each item in the list obtained from the 'pageHits' key.
        # Using .get() with a default empty list to handle the absence of 'pageHits'.
        for hit in data.get("pageHits", []):
            # Check if the current hit is not None before processing.
            if hit is not None:
                # Convert the hit dictionary to a PageHit instance and add it to the list.
                page_hits.append(PageHit.from_dict(hit))

        # 'data' dictionary is updated to hold the list of PageHit instances.
        data["pageHits"] = page_hits
        # Remove any keys from `data` that are not fields of the `ClickStream` dataclass
        # data = {key: value for key, value in data.items() if key in ClickStream.__annotations__}

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
            data["pageHits"] = [
                PageHit.from_dict(hit) if isinstance(hit, dict) else hit
                for hit in data["pageHits"]
            ]
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

    @classmethod
    def from_json(cls, json_file: str):
        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Handle nested structures
        data = ClickstreamLog._postprocess(data)

        return ClickstreamLog(**data)

    @classmethod
    def _postprocess(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        data["startTime"] = DateParse.parse_date(data["startTime"])
        data["lastFlush"] = DateParse.parse_date(data["lastFlush"])
        data["lastLogRotate"] = DateParse.parse_date(data["lastLogRotate"])
        data["clickStreams"] = [
            ClickStream.from_dict(cs) for cs in data.get("clickStreams", [])
        ]
        return data


class ClickstreamManager(object):
    """
    logging of client clicks
    """

    def __init__(
        self,
        root_path: str,
        rdf_namespace:str ="http://cms.bitplan.com/clickstream#",
        show_progress: bool = True,
        verbose: bool = True,
    ):
        """
        Constructor

        Args:
            root_path (str): the root path
            rdf_namespace (str): The base namespace URI for the RDF export.
            show_progress (bool): If True, show progress.
            verbose (bool): If True, print the output message.
        """
        self.root_path = root_path
        self.rdf_namespace = rdf_namespace
        self.clickstream_logs: List[ClickstreamLog] = []
        self.show_progress = show_progress
        self.verbose = verbose

    def get_progress(self, iterable, desc="Processing"):
        """
        Wrap an iterable with a progress bar if show_progress is True
        """
        if self.show_progress:
            return tqdm(iterable, desc=desc)
        else:
            return iterable

    def load_clickstream_logs(self, limit: Optional[int] = None) -> None:
        """
        Load all clickstream logs from the directory
        """
        # Find all json files in the directory
        json_files = glob.glob(os.path.join(self.root_path, "*.json"))
        # If a limit is set, truncate the file list
        if limit is not None:
            json_files = json_files[:limit]

        # Prepare tqdm iterator if required and tqdm is available
        iterator = self.get_progress(json_files, desc="Loading Clickstream Logs")

        total_clickstreams = 0

        # Load each file

        for json_file in iterator:
            try:
                # Parse the JSON file into ClickstreamLog
                clickstream_log = ClickstreamLog.from_json(json_file)
                self.clickstream_logs.append(clickstream_log)
                total_clickstreams += len(
                    clickstream_log.clickStreams
                )  # Count the clickstreams
            except json.JSONDecodeError as jde:
                # Handle JSON-specific parsing errors
                print(f"JSON decode error in file {json_file}: {jde.msg}")
                print(f"Error at line {jde.lineno}, column {jde.colno}")
            except Exception as e:
                tb = traceback.format_exc()  # This will give you the stack trace
                print(f"Error loading {json_file}: {e}")
                print(tb)  # Print stack trace to get more details about the exception
        # After importing, show the total counts
        total_logs = len(self.clickstream_logs)
        print(
            f"Imported {total_logs} clickstream logs with a total of {total_clickstreams} clickstreams."
        )

    def serialize_batch(
        self, g: Graph, rdf_file: str, file_counter: int, rdf_format: str
    ) -> None:
        """
        Serializes a batch of RDF data to a file.

        Args:
            g (Graph): The RDF graph to serialize.
            rdf_file (str): The base name for the RDF file.
            file_counter (int): The current file count for naming.
            rdf_format (str): The format to serialize the RDF data.

        """
        batch_file = f"{rdf_file}_part{file_counter:03}.{rdf_format}"
        g.serialize(destination=batch_file, format=rdf_format)
        if self.verbose:
            print(f"Exported RDF to {batch_file}")

    def add_stream_properties_to_graph(
        self, g: Graph, CS: Namespace, stream: Any, entity_counter: int
    ) -> int:
        """
        Adds the properties of a clickstream to the RDF graph.

        Args:
            g (Graph): The graph to which the properties will be added.
            CS (Namespace): The namespace for clickstream data.
            stream (Any): The clickstream object containing the data.
            entity_counter (int): A counter for creating unique entities.

        Returns:
            int: The updated entity counter after adding the properties.
        """
        stream_uri = URIRef(f"{CS}clickstream/{entity_counter}")
        entity_counter += 1

        # Add properties to the stream URI
        g.add((stream_uri, RDF.type, CS.ClickStream))
        g.add((stream_uri, CS.url, Literal(stream.url)))
        g.add((stream_uri, CS.ip, Literal(stream.ip)))
        g.add((stream_uri, CS.domain, Literal(stream.domain)))
        g.add((stream_uri, CS.userAgentHeader, Literal(stream.userAgentHeader)))
        g.add(
            (
                stream_uri,
                CS.timeStamp,
                Literal(stream.timeStamp.isoformat(), datatype=XSD.dateTime),
            )
        )

        # Optional referrer information
        if stream.referrer:
            g.add((stream_uri, CS.referrer, Literal(stream.referrer)))

        # User Agent details
        ua_uri = URIRef(f"{CS}useragent/{entity_counter}")
        entity_counter += 1
        g.add((ua_uri, RDF.type, CS.UserAgent))
        g.add((ua_uri, CS.hasSyntaxError, Literal(stream.userAgent.hasSyntaxError)))
        g.add((ua_uri, CS.hasAmbiguity, Literal(stream.userAgent.hasAmbiguity)))
        g.add((ua_uri, CS.ambiguityCount, Literal(stream.userAgent.ambiguityCount)))
        g.add((ua_uri, CS.userAgentString, Literal(stream.userAgent.userAgentString)))
        g.add((stream_uri, CS.userAgent, ua_uri))

        # Page Hits
        for hit in stream.pageHits:
            hit_uri = URIRef(f"{CS}pagehit/{entity_counter}")
            entity_counter += 1
            g.add((hit_uri, RDF.type, CS.PageHit))
            g.add((hit_uri, CS.path, Literal(hit.path)))
            g.add(
                (
                    hit_uri,
                    CS.timeStamp,
                    Literal(hit.timeStamp.isoformat(), datatype=XSD.dateTime),
                )
            )
            g.add((stream_uri, CS.pageHits, hit_uri))

        return entity_counter

    def export_to_rdf(
        self,
        rdf_file: str,
        batch_size: int,
        rdf_format: str = "nt",
    ) -> None:
        """
        Export clickstream logs to RDF files in batches.
        :param rdf_file: The base file name to write the RDF data to.
        :param batch_size: The number of clickstream records per file.
        :param rdf_format: The RDF serialization format to use (default is "nt").
        """
        # Namespace definition
        CS = Namespace(self.rdf_namespace)

        # Initialize variables
        file_counter = 1
        entity_counter = 1
        g = Graph()
        g.bind("cs", CS)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(rdf_file), exist_ok=True)
        iterator = self.get_progress(self.clickstream_logs, desc="Export Progress")

        for log in iterator:
            for stream in log.clickStreams:
                entity_counter = self.add_stream_properties_to_graph(
                    g, CS, stream, entity_counter
                )

                # If batch size is reached, serialize and save to file
                if entity_counter % batch_size == 0:
                    self.serialize_batch(g, rdf_file, file_counter, rdf_format)
                    file_counter += 1
                    g = Graph()  # Reset the graph for the next batch
                    g.bind("cs", CS)

        # Serialize and save any remaining triples that didn't fill up the last batch
        if len(g):
            self.serialize_batch(g, rdf_file, file_counter, rdf_format)

    def reload_graph(self, rdf_file_pattern: str, rdf_format: str = "nt") -> Graph:
        """
        Reloads the RDF data from a batch of files into the clickstream logs.

        Args:
            rdf_file_pattern (str): The file pattern to search for RDF files.
                                    A wildcard '*' will be appended if not present.
            rdf_format (str): The RDF serialization format of the files (default is "nt").

        Returns:
            Graph: The RDF graph populated with data from the files.
        """
        # Ensure the pattern ends with a wildcard, append if necessary
        if not rdf_file_pattern.endswith("*"):
            rdf_file_pattern += "*"

        # Find all files matching the pattern
        rdf_files = glob.glob(rdf_file_pattern)

        # Initialize a new RDF graph
        g = Graph()

        # Use a progress bar if available or simply iterate over files
        try:
            iterator = self.get_progress(rdf_files, desc="Loading graph")
        except AttributeError:
            # If get_progress is not defined, fall back to simple iteration
            iterator = rdf_files

        for rdf_file in iterator:
            # Parse each RDF file and add it to the graph
            g.parse(rdf_file, format=rdf_format)

        # After loading all files, return the populated graph
        return g
