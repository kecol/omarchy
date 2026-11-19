# bundled-agent-catalog Specification

## Purpose

Provide consistent product metadata from one bundled catalog while keeping menu representation separate from guard and launch-policy authority.

## Requirements

### Requirement: Recognize both supported menu namespaces

The bundled-catalog projection SHALL recognize object-valued product rows under `setup.default.agent.<name>` and `agent.harness.<name>` using the existing lowercase-letter, digit and hyphen selection grammar. It SHALL exclude unrelated IDs, submenu roots and nested descendants. Catalog membership SHALL NOT imply installation, Container support or permission to launch.

#### Scenario: Future product in either supported namespace

- **WHEN** the bundled catalog declares a new matching product in either supported namespace without a definition or manual registration
- **THEN** the projection includes that product's final ID segment as its logical name without consulting a product-name allowlist
- **AND** installed-command and runtime-definition checks remain the callers' responsibility

#### Scenario: Unrelated menu rows are not products

- **WHEN** menu input contains submenu roots, nested descendants, unrelated namespaces, uppercase or underscore variants, null rows or array rows
- **THEN** those rows do not enter the product projection

### Requirement: Preserve projection ordering and labels

The projection SHALL return only name/label records in source row enumeration order. It SHALL retain duplicate logical names and each row's existing truthy-label-or-source-ID fallback. It SHALL NOT sort, assign namespace precedence, coerce truthy invalid labels into strings or silently deduplicate records.

#### Scenario: Mixed namespaces retain source order

- **WHEN** matching legacy and modern rows are interleaved in the bundled data
- **THEN** records retain their source enumeration order regardless of namespace
- **AND** each missing or falsy label falls back to that row's unchanged source ID

#### Scenario: Duplicate names remain visible to caller validation

- **WHEN** both supported namespaces declare the same logical product name
- **THEN** both records remain in the projection
- **AND** the picker refuses duplicate names while guard discovery retains its existing identical-name mapping behavior

#### Scenario: Invalid truthy label is not repaired

- **WHEN** a matching row has a truthy non-string label
- **THEN** the projection retains that value for caller validation
- **AND** the picker rejects it while guard discovery remains names-only

### Requirement: Keep catalog projection data-only

The projection SHALL use only the supplied bundled metadata and perform no I/O or execution. Callers SHALL retain their bundled-only catalog reads. Catalog discovery SHALL NOT execute menu fields, consult user overlays or project/provider/account state as product sources, or broaden process-recognition and launch authority.

#### Scenario: Effectful menu fields do not execute

- **WHEN** matching product rows contain action, guard or provider fields
- **THEN** discovery returns only the projected name/label data without executing those fields or probing the product
- **AND** the catalog read does not save defaults, synchronize live guards, prepare an image or launch an agent

### Requirement: Preserve existing parsing and failure distinctions

The projection SHALL retain the existing limited comment/trailing-comma parsing, flat/wrapped object handling and malformed-input empty-list behavior. Callers SHALL preserve their distinct empty-list handling and propagate missing-file/module, Node failure and timeout errors without a UI-parser, stale-data or Host-execution fallback.

#### Scenario: Malformed metadata retains distinct caller outcomes

- **WHEN** bundled text is malformed or produces no catalog rows
- **THEN** the picker refuses the empty catalog
- **AND** guard discovery may continue through its existing definitions and explicit registrations without claiming complete catalog coverage

#### Scenario: Transport failure does not become an empty success

- **WHEN** the bundled file or reader module is unavailable, or the reader process fails or times out
- **THEN** the caller propagates failure rather than replacing it with an empty catalog or selecting a Host launch

### Requirement: Retain caller-owned limits and checks

Guard discovery and the picker SHALL retain their separate validation and transport boundaries. Both SHALL keep their five-second reader timeout and existing environment handling. Guards SHALL retain their one-MiB response and 256-entry limits, name/role checks and installed-only resolution. The picker SHALL retain its nonempty 128-record limit, name/duplicate validation and printable nonempty labels of at most 80 characters.

#### Scenario: Modern rows do not bypass limits or selection policy

- **WHEN** modern-format metadata produces an oversized or invalid response for either caller
- **THEN** that caller rejects it under its existing limits and validation
- **AND** picker cancellation, unavailable-default presentation and explicit Host/Container selection remain unchanged
