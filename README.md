# coverpack

## Geyser mappings

By default the converter writes safe Geyser mappings only for runtime Java item
IDs that Geyser can actually resolve. Resource-only Java `assets/**/items`
definitions such as `harshlands:baubles/amulet_slot` are copied into the
Bedrock resource pack/atlas, but they are not emitted into `geyser_mappings.json`
unless the Java server really registers those custom items.

For ItemsAdder/Oraxen/Nexo/CraftEngine-style virtual items, provide the plugin
config or generated mapping data that contains the vanilla base item plus
`custom_model_data`/damage predicates. The fallback base item is
`minecraft:paper` and can be changed with `SG_DEFAULT_BASE_ITEM`.

Only enable custom Java registry mappings when the server registry contains the
custom IDs used by the pack:

```powershell
$env:GEYSER_ALLOW_CUSTOM_JAVA_ITEMS = "true"
python manager.py
```

If Geyser logs `unknown Java item`, leave that env var disabled and supply the
plugin's base-item/CMD mapping instead.

## Font glyphs

Custom Java bitmap fonts are converted to Bedrock `font/glyph_XX.png` pages and
`font/glyph_sizes.bin`. Keep `.bin` files in the pack output; deleting
`glyph_sizes.bin` can make glyph images render incorrectly or not at all.
