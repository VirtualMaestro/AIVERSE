---
name: aiverse-building-gen
description: Generate enterable AIVERSE buildings from axis-aligned boxes - floors, slabs, outer walls with a seeded door and windows, an interior partition, switchback stairs, roof, loot spots and door points - sized for the game's agent and step height, for FPS maps, AABB navmeshes, cover maps or any box-collision world.
---

# building-gen

Use when a map needs many enterable houses without hand-placed walls (towns, raid sites, cover). The legacy
`engine/actor` map format wires it from data (`buildings`, docs/fps.md § Generated buildings); other hosts call the library
directly until the map block is shared (debt G2/G4 in `docs/no-genre-split-audit.md`).

1. Read `engine/systems/BuildingGen.h` (namespace `aiverse::lib::systems`).
2. Definition: `BuildingDef` or `readBuildingDef(json, "path")` - `width` / `depth` (6..200 m), `floors` 1..10,
   `floorHeight`, `wall`, `slab`, `door` [width, height], `window` [width, height, sill, spacing], `stair`
   [width, run, max rise], `partition`, `roof`. Always overwrite `agentRadius`, `agentHeight` and `maxStepRise`
   with the owner's motor so every doorway, landing and tread fits; errors name the path.
3. `generateBuilding(def, seed, origin, yaw)` (yaw in quarter turns) returns boxes in world space plus
   `lootSpots`, `door` / `doorOutside`, per-flight `stairs` (bottom, top) and `stairHalls` (open floor beside each end,
   reachable on a navmesh; walk the flight itself straight), or nullopt when it does not fit (the door moves to another
   side when the seeded one has no room).
4. Put `origin.y` at ground height minus `slab` so the ground floor is flush with the terrain (no threshold step;
   the FPS module does this). Add the boxes to the owner's static collision with ids from a reserved range (FPS: `kBuildingColliderBase`),
   rebuild navigation for the region (`skills/world/aiverse-navmesh`), spawn loot on `lootSpots` through the
   loot owner, use `doorOutside` / `stairs` as bot waypoints.
5. Determinism: Fixed math; the same definition, seed, origin and yaw give the same boxes everywhere, so a
   client can regenerate instead of downloading geometry (bind the map content hash).
6. Check: `tests/libraries/building_tests.cpp` (CTest `library_building_gen`: door and outside clear for the
   agent, supported loot spots, headroom above every tread of every flight, 40 seeded variants, yaw, invalid and
   JSON cases) and `buildings` in `tests/fps/tests.cpp` (the FPS motor walks in and climbs a floor). Not implied:
   meshes / materials (boxes only), rotated walls, furniture, destructible walls.

Build selection: `AIVERSE::lib_building_gen` (depends on `aiverse_engine`); native OBJECT modules call
`aiverse_native_use_libraries(target building-gen)`.
