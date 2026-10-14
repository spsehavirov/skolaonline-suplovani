"""Publish XML with its filter snapshot, and load/archive the pair together."""

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from .filters import FilterPolicy, build_policy, parse_date
from .settings import SnapshotSettings, read_config


def prepare_download(config_path, requested_date=None, args=None):
    config = read_config(config_path)
    report_date = parse_date(requested_date)
    policy = build_policy(config["settings"], report_date, args)
    return config, report_date, policy


def sidecar_path(xml_path):
    return Path(str(xml_path) + ".filters.json")


def xml_date(root):
    text = root.findtext(".//Kalendar/Datum")
    if not text:
        raise ValueError("XML is missing Kalendar/Datum")
    return datetime.fromisoformat(text).date()


def settings_for_xml(xml_path, settings):
    """Validate the handoff before any exporter can modify existing outputs."""
    xml_path = Path(xml_path)
    report_date = xml_date(ET.parse(xml_path).getroot())
    snapshot = settings.snapshot()
    sidecar = sidecar_path(xml_path)
    if sidecar.exists():
        with sidecar.open(encoding="utf-8") as stream:
            data = json.load(stream)
        if (not isinstance(data, dict) or set(data) != {"version", "date", "xml", "filters"}
                or type(data["version"]) is not int or data["version"] != 1):
            raise ValueError(f"Invalid filter snapshot: {sidecar}")
        if data["xml"] != xml_path.name or data["date"] != report_date.isoformat():
            raise ValueError(f"Filter snapshot does not match the XML name/date: {sidecar}")
        policy = FilterPolicy.from_dict(data["filters"])
    else:
        policy = build_policy(snapshot.as_dict(), report_date)
    return SnapshotSettings(snapshot.as_dict(), policy)


def publish_xml(content, report_date, config, policy):
    """Make complete sidecar visible first, then complete XML; never overwrite."""
    actual_date = xml_date(ET.fromstring(content))
    if actual_date != report_date:
        raise ValueError(f"Downloaded XML date {actual_date} does not match requested date {report_date}")
    directory = Path(config["settings"].get("watch_folder", "./watch"))
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"so_suplovani_students-{report_date.isoformat()}.xml"
    sidecar = sidecar_path(destination)
    if destination.exists() or sidecar.exists():
        raise FileExistsError(f"A pending XML or filter snapshot already exists: {destination}")
    data = {"version": 1, "date": report_date.isoformat(), "xml": destination.name,
            "filters": policy.to_dict()}
    sidecar_created = published = False
    with tempfile.TemporaryDirectory(prefix=".so-supl-", dir=directory) as temporary:
        staged_xml = Path(temporary) / "input"
        staged_json = Path(temporary) / "filters"
        with staged_xml.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        with staged_json.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Hard links give atomic publication with exclusive destination names.
            # Staging is on the same filesystem as the watched directory.
            os.link(staged_json, sidecar)
            sidecar_created = True
            os.link(staged_xml, destination)
            published = True
        finally:
            if sidecar_created and not published:
                sidecar.unlink()
    return str(destination)


def archive_xml(xml_path, processed_dir):
    """Preserve prior archives and keep inputs if either archive link fails."""
    xml_path, processed_dir = Path(xml_path), Path(processed_dir)
    sidecar = sidecar_path(xml_path)
    processed_dir.mkdir(parents=True, exist_ok=True)
    destination = processed_dir / xml_path.name
    if destination.exists() or sidecar_path(destination).exists():
        processed_dir = Path(tempfile.mkdtemp(prefix=xml_path.stem + "-", dir=processed_dir))
        destination = processed_dir / xml_path.name
    linked = []
    try:
        os.link(xml_path, destination)
        linked.append(destination)
        if sidecar.exists():
            target = sidecar_path(destination)
            os.link(sidecar, target)
            linked.append(target)
    except OSError:
        for target in linked:
            target.unlink()
        raise
    xml_path.unlink()
    if sidecar.exists():
        sidecar.unlink()
    return destination
