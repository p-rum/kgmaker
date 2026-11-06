# Interface Markdown (T020 source candidate)

The pure `architecture_render.render_interface_markdown(document)` returns a bounded
Markdown string for one existing interfaces ViewDocument. It does not load sources,
project interfaces, resolve owners/contracts, read a store or run an application.

```python
from kgmaker.architecture_render import render_interface_markdown
report = render_interface_markdown(validated_interface_document)
```

The T019 adapter supports this format only for interfaces, using the same validated
catalog, baseline and context selection as JSON. JSON remains the default.

```sh
kgmaker architecture interfaces --root /repo --catalog http-providers --interface-capture interfaces.json --format markdown
kgmaker architecture interfaces --root /repo --catalog http-consumers --interface-capture interfaces.json --format markdown --strict
kgmaker architecture interfaces --root /repo --catalog kafka --interface-capture interfaces.json --format markdown
```

The input is T019's explicit versioned capture bundle, not an arbitrary bare view
file passed as a bundle. T019's separate `--capture-local --workspace` remains an
explicit local parser/read phase with original-index preflight; choosing Markdown
introduces no additional capture or publication. Topology/explain Markdown, export
files and a generic explanation resolver are outside T020.

Fixed headings show the selected view/content fingerprint, baseline, snapshot
and coverage, provided/used interface
rows, mandatory generated/unclassified rows, contract revisions, unresolved/stale
boundaries and original evidence. HTTP definition versus terminal intent, Kafka
realm/group/pattern, declaration versus expectation, and static versus runtime
availability stay distinct. Logical IDs are retained, not replaced by display
labels or contract fingerprints. Unknown owner/target/evidence remains visible;
zero rows describe the selected capture, not absence of application integrations.

Every row links to an internal SHA256-derived evidence anchor. Those anchors are
the only generated HTML/link targets; untrusted text is escaped and cannot create
headings, table rows, links, HTML or fenced blocks. Protocol/domain/email
punctuation is entity-escaped as well, preventing bare supplied URL text from
becoming GFM autolink source while retaining its decoded visible text. IDs round-trip as decoded text.
CR/LF and Unicode line separators are displayed as `⏎`; tabs as `⇥`; other control
formatting uses visible code-point markers in labels. Unsafe immutable IDs and
recognized credentials are rejected by the existing public privacy boundary with
fixed errors rather than silently renamed. Known public fields are displayed;
raw attributes, contract/schema bodies and private source roots are not dumped.

Evidence kind, supporting/contradicting/unknown buckets, resolution, freshness,
context/release and runtime/data/deployment fields are not rewritten. The renderer
never attests the physical checkout; source observation is NOT_CHECKED. Supplied
source locators/hashes are text, not filesystem or external links. T018's topology
explanation API is not called to manufacture interface drill-down authority.

Input budgets apply before model normalization: 100,000 occurrences, depth40,
10,000-item containers,16,384-character scalars and1,000,000 total input characters.
Output is bounded to4,000,000 UTF-8 bytes before emission. Cycles, shared amplification,
malformed known fields and unsupported schemas/kinds fail safely; rows are never
silently cut while retaining COMPLETE coverage. Valid partial output returns0,
strict incomplete4; invalid2 and fingerprint conflict3 retain T019's no-output rule.

## Development parser validation

The renderer has no Markdown runtime package dependency. Tests explicitly prepare
hash-pinned `markdown-it-py==3.0.0` and `mdurl==0.1.2` from
`tests/requirements-markdown.txt`, enable the table rule, and inspect real AST
headings/cells/text/internal links/HTML tokens. CI's unittest job requires this
parser; absent optional local tooling is a reported module skip, not a parser PASS.

Local preparation must use a task-specific directory/environment, preserving any
frozen shared environment inputs. This source candidate was tested with parser
packages only in `/workspace/t020-dev/site-packages`; no renderer path installs them.
The public feature RED and current focused results are recorded in change100.
No full/native/ready or upstream-final-validation claim is implied by this document.
