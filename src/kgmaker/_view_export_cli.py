"""Shared CLI transport for publishing one explicit captured view."""
import math
import sys
import time

from .analysis_model import canonical, decode_json
from .view_store import (
    ViewExportError, ViewPublication, export_path, export_snapshot_stamp,
    publish_view_artifacts, read_export_snapshot,
)


def export_snapshot_artifacts(args, snapshot, kind, decode_snapshot, render_snapshot, *, max_input_bytes):
    """Bind one decoded snapshot to the transaction and write its confirmed receipt."""
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ViewExportError('INVALID_EXPORT_TIMEOUT')
    root = args.root
    output = export_path(root, args.output)
    snapshot = export_path(root, snapshot)
    cancel = None if args.cancel_file is None else export_path(root, args.cancel_file)
    if ((snapshot.parent == output and snapshot.name.casefold() == 'manifest.json')
            or (cancel is not None and cancel.is_relative_to(output))):
        raise ViewExportError('INVALID_EXPORT_PATH')
    deadline = time.monotonic() + args.timeout

    def checkpoint():
        if cancel is not None and (root / export_path(root, cancel)).exists():
            raise ViewExportError('CANCELLED', 130)
        if time.monotonic() >= deadline:
            raise ViewExportError('EXPORT_TIMEOUT', 1)

    checkpoint()
    raw, _ = read_export_snapshot(root, snapshot, max_input_bytes)
    model = decode_snapshot(decode_json(raw.decode('utf-8'), 'view export snapshot'))

    def render():
        fingerprint, files = render_snapshot(model)
        if args.expected_fingerprint is not None and args.expected_fingerprint != fingerprint:
            raise ViewExportError('EXPECTED_FINGERPRINT_MISMATCH', 3)
        return fingerprint, files

    def verify_input():
        try:
            current, stamp = read_export_snapshot(root, snapshot, max_input_bytes)
        except (OSError, ViewExportError):
            raise ViewExportError('EXPORT_INPUT_CHANGED', 3) from None
        if current != raw:
            raise ViewExportError('EXPORT_INPUT_CHANGED', 3)
        return stamp

    def verify_input_stamp(stamp):
        try:
            current = export_snapshot_stamp(root, snapshot)
        except (OSError, ViewExportError):
            raise ViewExportError('EXPORT_INPUT_CHANGED', 3) from None
        if current != stamp:
            raise ViewExportError('EXPORT_INPUT_CHANGED', 3)

    publication = ViewPublication()
    try:
        try:
            publish_view_artifacts(root, output, kind, render, checkpoint=checkpoint,
                                   verify_input=verify_input, verify_input_stamp=verify_input_stamp,
                                   publication=publication)
        except OSError:
            raise ViewExportError('EXPORT_IO_ERROR', 1) from None
        sys.stdout.write(canonical(publication.manifest) + '\n')
        sys.stdout.flush()
        return 0
    except KeyboardInterrupt:
        if publication.manifest is None:
            raise
        raise ViewExportError('EXPORT_RECEIPT_INTERRUPTED', 1) from None
