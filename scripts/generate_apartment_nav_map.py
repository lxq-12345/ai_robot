#!/usr/bin/env python3
"""Generate a 2D Nav2 occupancy map from apartment ground-level collisions."""

import argparse
import math
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_arguments():
    workspace = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world",
        type=Path,
        default=workspace / "src/ai_robot_sim/worlds/apartment_v1.3.world",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=workspace / "src/ai_robot_sim/maps/apartment_v1.3_nav",
    )
    parser.add_argument("--resolution", type=float, default=0.05)
    parser.add_argument("--origin-x", type=float, default=-0.50)
    parser.add_argument("--origin-y", type=float, default=-0.50)
    parser.add_argument("--max-x", type=float, default=6.70)
    parser.add_argument("--max-y", type=float, default=8.00)
    parser.add_argument("--projection-height", type=float, default=0.40)
    return parser.parse_args()


def ground_level_boxes(world_path, projection_height):
    root = ET.parse(world_path).getroot()
    model = root.find(".//model[@name='apartment_house']")
    if model is None:
        raise RuntimeError("apartment_house model is missing")
    boxes = []
    for collision in model.findall(".//collision"):
        size_text = collision.findtext("./geometry/box/size")
        if not size_text:
            continue
        pose = [float(value) for value in collision.findtext("pose").split()]
        size = [float(value) for value in size_text.split()]
        if any(abs(angle) > 1e-9 for angle in pose[3:]):
            raise RuntimeError(
                f"rotated collision is not supported: {collision.get('name')}"
            )
        z_min = pose[2] - size[2] / 2.0
        z_max = pose[2] + size[2] / 2.0
        if z_min > projection_height or z_max <= 0.0:
            continue
        boxes.append(
            (
                pose[0] - size[0] / 2.0,
                pose[0] + size[0] / 2.0,
                pose[1] - size[1] / 2.0,
                pose[1] + size[1] / 2.0,
            )
        )
    if not boxes:
        raise RuntimeError("no ground-level apartment collisions found")
    return boxes


def main():
    args = parse_arguments()
    width = math.ceil((args.max_x - args.origin_x) / args.resolution)
    height = math.ceil((args.max_y - args.origin_y) / args.resolution)
    boxes = ground_level_boxes(args.world, args.projection_height)
    pixels = bytearray([254] * (width * height))
    for row in range(height):
        y = args.origin_y + (height - row - 0.5) * args.resolution
        for column in range(width):
            x = args.origin_x + (column + 0.5) * args.resolution
            if any(
                x_min <= x <= x_max and y_min <= y <= y_max
                for x_min, x_max, y_min, y_max in boxes
            ):
                pixels[row * width + column] = 0

    pgm_path = Path(f"{args.output_prefix}.pgm")
    yaml_path = Path(f"{args.output_prefix}.yaml")
    pgm_path.parent.mkdir(parents=True, exist_ok=True)
    with pgm_path.open("wb") as stream:
        stream.write(f"P5\n{width} {height}\n255\n".encode("ascii"))
        stream.write(pixels)
    yaml_path.write_text(
        "\n".join(
            [
                f"image: {pgm_path.name}",
                "mode: trinary",
                f"resolution: {args.resolution:.2f}",
                f"origin: [{args.origin_x:.2f}, {args.origin_y:.2f}, 0.0]",
                "negate: 0",
                "occupied_thresh: 0.65",
                "free_thresh: 0.25",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"generated {pgm_path} ({width}x{height}, {len(boxes)} boxes)")
    print(f"generated {yaml_path}")


if __name__ == "__main__":
    main()
