# This workflow will build each Maven module and optionally build a
# Docker image for it, using the Flume reusable workflow.

name: Build Maven Project (4 services via matrix)

on:
  push:
    branches: [ deleted-case-j ]
  pull_request: {}
  workflow_dispatch: {}

jobs:
  ci-workflow:
    # 👇 新增 —— 让同一个 job 在 4 个服务上并行运行
    strategy:
      matrix:
        svc: [ gateway, review-deleted-case, service-b, service-c ]
      fail-fast: false  # 任意一个失败，不取消其他 job

    # 🔗 调用 Flume 可复用工作流（保持不变）
    uses: fiserv/flume-reuseable-workflows/.github/workflows/maven.yml@main
    secrets: inherit

    with:
      # --- REQUIRED PARAMETERS ---
      apm: APM0001099

      # 🔄 动态应用服务名
      app_name: ${{ matrix.svc }}

      # 版本号保持不变
      app_version: 0.0.1-SNAPSHOT

      # Java 版本
      java_version: '21'

      # --- OPTIONAL PARAMETERS (保持现有设置) ---
      sonar_enable: true
      sonar_sourcepath: src/main/java
      sonar_args: '-Dsonar.java.binaries=target'

      # --- CONTAINERIZE ---
      # 为每个服务生成独立镜像：edwardjing/<service>:<git-sha>
      image_name: edwardjing/${{ matrix.svc }}
      image_tag:  ${{ github.sha }}
