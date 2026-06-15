from physicalEngine import ParticleWorld, STONE, WATER, SimulationConfig, Vec3, WorldBounds


def build_scene():
    config = SimulationConfig(
        time_step=1.0 / 90.0,
        smoothing_radius=0.34,
        constraint_iterations=10,
        bounds=WorldBounds(Vec3(-3.0, -0.2, -3.0), Vec3(3.0, 5.0, 3.0)),
    )
    world = ParticleWorld(config)

    # A rock is represented as many particles locked by stable distance constraints.
    world.create_box_cluster(
        origin=Vec3(-0.7, 0.25, -0.35),
        size=(6, 3, 4),
        spacing=0.18,
        material=STONE,
        group="rock",
        fixed=True,
    )

    # Water remains unconstrained, so particles can separate, gather and flow.
    world.create_fluid_block(
        origin=Vec3(-0.6, 3.3, -0.45),
        size=(6, 6, 5),
        spacing=0.16,
        material=WATER,
        group="water",
    )
    return world


def main():
    world = build_scene()
    for frame in range(180):
        snapshot = world.step(substeps=2)
        if frame % 30 == 0:
            water = [p for p in snapshot["particles"] if p["group"] == "water"]
            avg_y = sum(p["position"][1] for p in water) / len(water)
            max_force = max((sum(component * component for component in p["force"]) ** 0.5 for p in water), default=0.0)
            print(
                f"frame={frame:03d} "
                f"time={snapshot['time']:.2f}s "
                f"particles={snapshot['particle_count']} "
                f"water_avg_y={avg_y:.3f} "
                f"water_max_force={max_force:.2f}"
            )


if __name__ == "__main__":
    main()
