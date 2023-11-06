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
from typing import Any, Dict, List, Optional


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

@dataclass
class ClickStream:
    url: str
    ip: str
    domain: str
    userAgentHeader: str
    timeStamp: datetime
    pageHits: List[PageHit]
    userAgent: UserAgent
    referrer: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ClickStream":
        data["timeStamp"] = parse_date(data["timeStamp"])
        data["pageHits"] = [PageHit.from_dict(hit) for hit in data.get("pageHits", [])]
        data["userAgent"] = UserAgent(**data["userAgent"])
        return ClickStream(**data)


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

        # Convert date strings to datetime objects
        data["startTime"] = cls._parse_date(data["startTime"])
        data["lastFlush"] = cls._parse_date(data["lastFlush"])
        data["lastLogRotate"] = cls._parse_date(data["lastLogRotate"])

        return cls(**data)


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
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
