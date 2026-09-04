#!/usr/bin/env bash
#
# check_cross_repo_links.sh — every librescrs.github.io URL committed in the
# code repositories must resolve against a locally built copy of this site.
#
#   usage: bash tools/check_cross_repo_links.sh <workspace-root> <public-dir>
#
# <workspace-root> holds the code repositories as sibling directories.
# <public-dir> is the output of `hugo --minify -d <public-dir>`.
#
# NOT WIRED INTO CI, ON PURPOSE. The deploy workflow checks out this
# repository alone, so in CI <workspace-root> would hold no code repositories
# at all and the check would report "checked 0 references / dead: 0" — a green
# result that proves nothing. Run it locally before publishing; the
# translation-completeness gate next to it needs only content/ and is the one
# CI runs.
#
# No network call: a URL's path is mapped onto <public-dir>/<path>/index.html,
# which is exactly what GitHub Pages serves for it.

set -u

root=${1:-}
public=${2:-}

if [ -z "$root" ] || [ -z "$public" ]; then
    echo "usage: $0 <workspace-root> <public-dir>" >&2
    exit 2
fi
if [ ! -d "$root" ]; then
    echo "workspace root is not a directory: $root" >&2
    exit 2
fi
if [ ! -d "$public" ]; then
    echo "public directory is not a directory: $public" >&2
    echo "  build it first:  hugo --minify -d $public" >&2
    exit 2
fi

REPOS="LibreMiddleware LibreAgent LibreLinux LibreCelik LibreKDE LibreDarwin LibreMac"

refs=$(mktemp)
trap 'rm -f "$refs"' EXIT

for repo in $REPOS; do
    [ -d "$root/$repo/.git" ] || continue
    while IFS= read -r rel; do
        file="$root/$repo/$rel"
        [ -f "$file" ] || continue
        grep -ohiE 'https?://librescrs\.github\.io[^[:space:]<>")'"'"'`]*' "$file" 2>/dev/null |
        while IFS= read -r url; do
            # Strip what a surrounding document format glued onto the URL:
            # HTML entities, escaped newlines, backslash line continuations,
            # and trailing sentence punctuation.
            url=${url%%&quot;*}
            url=${url%%&gt;*}
            url=${url%%'\n'*}
            url=${url%%'\'*}
            url=${url%%'&'*}
            url=$(printf '%s' "$url" | sed -E 's/[.,;:!?]+$//')
            [ -n "$url" ] || continue
            printf '%s\t%s/%s\n' "$url" "$repo" "$rel"
        done
    done < <(git -C "$root/$repo" ls-files)
done | sort -u > "$refs"

checked=0
dead=0

while IFS=$'\t' read -r url source; do
    [ -n "$url" ] || continue
    checked=$((checked + 1))

    # Path part, host-insensitively: everything after the host, minus any
    # query or fragment.
    path=$(printf '%s' "$url" | sed -E 's#^https?://[^/]+##; s/[?#].*$//')
    path=${path#/}
    path=${path%/}

    if [ -z "$path" ]; then
        target="$public/index.html"
    elif [ -f "$public/$path" ]; then
        target="$public/$path"
    else
        target="$public/$path/index.html"
    fi

    if [ ! -f "$target" ]; then
        dead=$((dead + 1))
        echo "DEAD: $url"
        echo "   referenced from: $source"
    fi
done < "$refs"

echo "---"
echo "checked $checked distinct (url, source) references"
echo "dead: $dead"

[ "$dead" -eq 0 ] || exit 1
exit 0
