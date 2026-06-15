# physicalEngine

一个基于粒子的 3D 物理计算核心，可作为 3D 引擎、工业仿真或交互式可视化的底层计算模块。

## 核心设计

引擎把所有物体都表示为粒子集合：

- 石头、金属块等稳定结构：由许多固体粒子组成，粒子之间通过距离约束保持稳定形状。
- 水等流体：由可自由运动的流体粒子组成，通过密度、压力、黏性、内聚力计算聚合和流动。
- 固液接触：通过邻域查询发现接近粒子，计算接触排斥、阻尼和摩擦，从而得到相对位置、受力和移动。

当前实现采用纯 Python 标准库，方便理解和扩展。后续可以把 `ParticleWorld.snapshot()` 返回的数据传给 OpenGL、PyQt3D、Unity、Unreal 或工业可视化系统做渲染。

## 模块

- `vector.py`：3D 向量计算。
- `material.py`：材料与相态定义，例如 `STONE`、`WATER`、`SAND`。
- `particle.py`：粒子状态，包含位置、速度、受力、密度、压力等。
- `spatial_hash.py`：空间哈希邻域查询，避免粒子两两全量计算。
- `constraint.py`：距离约束和固定点约束，用于稳定结构。
- `world.py`：仿真世界，负责力计算、积分、约束求解、边界碰撞和快照输出。
- `demo.py`：水落到石头粒子结构上的示例。

## 快速运行

在仓库根目录执行：

```powershell
python -m physicalEngine.demo
```

## 基本用法

```python
from physicalEngine import ParticleWorld, STONE, WATER, Vec3

world = ParticleWorld()

# 创建一块由稳定粒子结构组成的石头
world.create_box_cluster(
    origin=Vec3(-0.5, 0.2, -0.3),
    size=(5, 3, 4),
    spacing=0.18,
    material=STONE,
    group="rock",
    fixed=True,
)

# 创建一团水
world.create_fluid_block(
    origin=Vec3(-0.5, 2.5, -0.3),
    size=(5, 5, 4),
    spacing=0.16,
    material=WATER,
    group="water",
)

snapshot = world.step(substeps=2)
positions = [p["position"] for p in snapshot["particles"]]
```

## 已实现能力

- 3D 粒子系统
- 材料相态：固体、流体、颗粒
- 固体粒子稳定结构约束
- SPH 风格流体密度、压力、黏性和内聚计算
- 固体/流体局部接触、排斥、阻尼、摩擦
- 世界边界碰撞
- 空间哈希邻域查询
- 可序列化快照，便于接入渲染或工业系统

## 后续扩展方向

- 使用 NumPy、Cython、Rust 或 C++ 加速大规模粒子。
- 增加形状匹配约束，让固体结构在受力后保持更真实的刚体姿态。
- 增加碰撞网格，支持复杂工业模型边界。
- 增加材料标定和单位系统，满足工程仿真精度要求。
- 增加并行计算或 GPU 计算，用于更多粒子的实时仿真。
