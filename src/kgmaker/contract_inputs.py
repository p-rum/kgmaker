"""Bounded read-only captures for explicitly declared contracts and generation origin."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .analysis_model import safe_path
from .scanner import MAX_FILE_BYTES


def capture_file(root: Path, path: str, *, json_document=False) -> dict:
    target=safe_path(root,path)
    if target.stat().st_size>MAX_FILE_BYTES:
        raise ValueError('Explicit contract input exceeds the source capture limit')
    with target.open('rb') as stream:raw=stream.read(MAX_FILE_BYTES+1)
    if len(raw)>MAX_FILE_BYTES:
        raise ValueError('Explicit contract input exceeds the source capture limit')
    checksum=hashlib.sha256(raw).hexdigest()
    # Before/after bytes, including same-length replacement, are authoritative.
    with target.open('rb') as stream:after=stream.read(MAX_FILE_BYTES+1)
    if raw!=after:raise ValueError('Explicit contract input changed during capture')
    text=raw.decode('utf-8')
    result={'path':path,'raw_sha256':checksum,
            'source_sha256':hashlib.sha256(text.replace('\r\n','\n').replace('\r','\n').encode()).hexdigest()}
    if json_document:
        def pairs(items):
            result={}
            for key,value in items:
                if key in result:raise ValueError('Ambiguous duplicate JSON key')
                result[key]=value
            return result
        document=json.loads(text,object_pairs_hook=pairs)
        if not isinstance(document,dict):raise ValueError('Explicit JSON input must be an object')
        result['document']=document
    return result


def generation_origin(metadata, expected, generated_path):
    """Declaration provenance only; never an executable generator receipt."""
    if not isinstance(metadata,dict) or not isinstance(metadata.get('generated_files'),list):
        return 'UNKNOWN',None,'GENERATION_METADATA_INVALID'
    files=metadata['generated_files'];origin=metadata.get('source_contract')
    if (len(files)>2048 or any(not isinstance(p,str) for p in files)
            or generated_path not in files or not isinstance(origin,dict)
            or set(origin)!={'repo_id','path','sha256'}):
        return 'UNKNOWN',None,'GENERATION_METADATA_INVALID'
    import re
    if (origin.get('repo_id')!=expected['repo_id'] or origin.get('path')!=expected['path']
            or not isinstance(origin.get('sha256'),str)
            or re.fullmatch('[0-9a-f]{64}',origin['sha256']) is None):
        return 'UNKNOWN',None,'GENERATION_ORIGIN_REALM_UNKNOWN'
    if origin!=expected:return 'STALE',dict(origin),'GENERATED_CONTRACT_STALE'
    return 'VALID',dict(origin),None
