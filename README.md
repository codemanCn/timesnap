# timesnap

一个零依赖 Python CLI，用于遍历指定目录、把文件元数据快照保存到目标目录下的 `.timeSnap/`，并支持后续恢复。

## 安装

### 方式一：安装为系统命令行工具

```bash
git clone https://github.com/codemanCn/timesnap.git
cd timesnap
pip install .
timesnap --help
```

如果不想装到系统环境，可以安装到用户目录：

```bash
pip install --user .
```

### 方式二：直接从 Git 安装

```bash
pip install git+https://github.com/codemanCn/timesnap.git
timesnap --help
```

### 方式三：通过 Git 克隆后直接运行

```bash
git clone https://github.com/codemanCn/timesnap.git
cd timesnap
python -m timesnap --help
```

### 方式四：仅拉代码到本地某个目录

```bash
git clone https://github.com/codemanCn/timesnap.git /your/path/timesnap
cd /your/path/timesnap
python -m timesnap snapshot /path/to/project
```

### 环境要求

```bash
python --version
```

推荐 Python 3.10 及以上。

## 卸载

```bash
pip uninstall timesnap
```

## 命令

```bash
python -m timesnap --help
python -m timesnap snapshot /path/to/project
python -m timesnap snapshot /path/to/project --name release-1
python -m timesnap list /path/to/project
python -m timesnap restore /path/to/project 20260327-193000
python -m timesnap restore /path/to/project release-1 --no-overwrite
```

## 常见用法

```bash
# 为目录创建快照
python -m timesnap snapshot /path/to/project

# 指定快照名称
python -m timesnap snapshot /path/to/project --name before-cleanup

# 查看已有快照
python -m timesnap list /path/to/project

# 按快照恢复元数据
python -m timesnap restore /path/to/project before-cleanup
```

## 快照内容

- 相对路径
- 文件大小
- 文件权限
- 文件创建时间（平台支持时读取）
- 文件修改时间
- 文件访问时间

## 恢复范围

- 恢复现有文件的权限
- 恢复现有文件的修改时间和访问时间
- 不保存文件内容副本，因此不会恢复文件内容，也无法找回已删除文件

## 目录结构

```text
<target>/
  .timeSnap/
    snapshots/
      <snapshot_id>/
        manifest.json
```
