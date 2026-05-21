#!/usr/bin/env bash
# Adds all shadcn primitives used by the redesign.
# Run from frontend/ (or wherever components.json lives).

set -euo pipefail

npx shadcn@latest add \
  button \
  input \
  label \
  dropdown-menu \
  accordion \
  table \
  tooltip \
  dialog \
  separator \
  scroll-area \
  badge \
  skeleton \
  switch \
  select \
  textarea \
  form \
  sonner

# Recommended additional npm deps (skip any already installed):
# npm i lucide-react react-router-dom

echo "Done. Components are in src/components/ui/."
