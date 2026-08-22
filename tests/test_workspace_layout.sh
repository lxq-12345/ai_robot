#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for path in README.md AGENTS.md skills/会话管理协议.md plan mem learning learning/README.md learning/ROS2仿真机器人 learning/ROS2仿真机器人/README.md learning/ROS2仿真机器人/bks/PU1 learning/ROS2仿真机器人/assets/S1-1-M0 learning/ROS2仿真机器人/assets/S1-1-M1 src config scripts tests resources tests/README.md tests/contract tests/integration tests/system tests/helpers tests/scenario tests/evidence src/ai_robot_sim/test src/ai_robot_py_example/test; do
  if [[ ! -e "$project_root/$path" ]]; then
    echo "Required project path not found: $path" >&2
    exit 1
  fi
done

course_root="$project_root/learning/ROS2仿真机器人"
course_index="$course_root/README.md"
learning_plan="$project_root/plan/ROS2仿真机器人学习计划_v1.8.md"

for milestone in {0..6}; do
  for kind in source html; do
    path="$course_root/$kind/S1-1-M$milestone"
    if [[ ! -d "$path" ]]; then
      echo "Required learning directory not found: ${path#"$project_root/"}" >&2
      exit 1
    fi
  done
done

plan_unit_count=0
while IFS= read -r unit; do
  ((plan_unit_count += 1))
  source_matches=$(find "$course_root/source" -type f -name "$unit-*.md" | wc -l)
  if [[ "$source_matches" -lt 1 ]]; then
    echo "Learning plan unit has no current Markdown textbook: $unit" >&2
    exit 1
  fi
  if ! rg -q "$unit" "$course_index"; then
    echo "Learning plan unit missing from course index: $unit" >&2
    exit 1
  fi
done < <(sed -n 's/^#### \(S1-1-M[0-6]-L[1-4]\).*/\1/p' "$learning_plan")

if [[ "$plan_unit_count" -ne 20 ]]; then
  echo "Expected 20 learning units in v1.8 plan, found: $plan_unit_count" >&2
  exit 1
fi

source_count=$(find "$course_root/source" -type f -name '*.md' | wc -l)
html_count=$(find "$course_root/html" -type f -name '*.html' | wc -l)
if [[ "$source_count" -ne 21 || "$html_count" -ne 21 ]]; then
  echo "Expected 21 current Markdown/HTML chapters, found Markdown=$source_count HTML=$html_count" >&2
  exit 1
fi

while IFS= read -r source; do
  relative=${source#"$course_root/source/"}
  html="$course_root/html/${relative%.md}.html"
  if [[ ! -s "$html" ]]; then
    echo "Current textbook has no non-empty matching HTML: $relative" >&2
    exit 1
  fi
  if ! rg -q "source/$relative" "$course_index"; then
    echo "Current Markdown textbook missing from course index: $relative" >&2
    exit 1
  fi
  if ! rg -q "html/${relative%.md}.html" "$course_index"; then
    echo "Current HTML textbook missing from course index: ${relative%.md}.html" >&2
    exit 1
  fi
  for pattern in '^# S1-1-M' '所属开发单元' '所属学习子单元' '版本：v' '理解检查' '项目内依据'; do
    if ! rg -q "$pattern" "$source"; then
      echo "Current textbook missing required content '$pattern': $relative" >&2
      exit 1
    fi
  done
done < <(find "$course_root/source" -type f -name '*.md' | sort)

for obsolete_path in tests/unit tests/launch; do
  if [[ -e "$project_root/$obsolete_path" ]]; then
    echo "Obsolete test directory must not exist: $obsolete_path" >&2
    exit 1
  fi
done

if ! git -C "$project_root" check-ignore -q docs/.keep; then
  echo "docs/ must remain local-only and ignored by Git" >&2
  exit 1
fi

echo "Workspace layout check passed"
