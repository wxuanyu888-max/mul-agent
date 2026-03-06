"""Test script for Baidu Qianfan image understanding capabilities"""

import os
from mul_agent.brain.llm import LLMClient


def test_baidu_image_understanding():
    """测试百度千帆图片理解能力"""
    # 初始化客户端
    llm = LLMClient()

    print(f"当前提供商：{llm.provider}")
    print(f"是否可用：{llm.is_available()}")

    if not llm.is_available():
        print("错误：LLM 未配置，请设置环境变量")
        print("百度千帆：BAIDU_API_KEY, BAIDU_SECRET_KEY")
        print("Anthropic: ANTHROPIC_AUTH_TOKEN")
        return

    # 测试 1: 纯文本对话
    print("\n=== 测试 1: 纯文本对话 ===")
    response = llm.chat(message="你好，请用一句话介绍你自己")
    print(f"响应：{response.get('content', '')[:100]}...")

    # 测试 2: 图片 URL（如果有测试图片）
    print("\n=== 测试 2: 图片 URL 理解 ===")
    test_image_url = "https://picsum.photos/seed/test123/800/600.jpg"
    response = llm.chat(
        message="请描述这张图片的内容",
        images=[{"type": "url", "url": test_image_url}]
    )
    print(f"响应：{response.get('content', '')[:200]}...")

    # 测试 3: 本地图片文件（如果存在）
    print("\n=== 测试 3: 本地图片文件 ===")
    test_image_path = "test_image.png"
    if os.path.exists(test_image_path):
        response = llm.chat(
            message="请分析这张图片",
            images=[test_image_path]
        )
        print(f"响应：{response.get('content', '')[:200]}...")
    else:
        print(f"跳过：测试图片不存在 {test_image_path}")

    # 测试 4: Base64 图片
    print("\n=== 测试 4: Base64 图片 ===")
    # 创建一个简单的 1x1 像素的 PNG 作为测试
    import base64
    # 1x1 transparent PNG
    test_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    response = llm.chat(
        message="这是一个什么类型的图片",
        images=[{"type": "base64", "data": test_base64}]
    )
    print(f"响应：{response.get('content', '')[:100]}...")

    print("\n=== 测试完成 ===")


def test_multi_image_comparison():
    """测试多图片对比"""
    llm = LLMClient()

    if not llm.is_available():
        print("LLM 未配置")
        return

    print("\n=== 测试：多图片对比 ===")

    # 使用两个不同的示例图片 URL
    image1 = {"type": "url", "url": "https://picsum.photos/seed/img1/400/300.jpg"}
    image2 = {"type": "url", "url": "https://picsum.photos/seed/img2/400/300.jpg"}

    response = llm.chat(
        message="请对比这两张图片的相似之处和不同之处",
        images=[image1, image2]
    )

    print(f"响应：{response.get('content', '')[:300]}...")
    print(f"Token 使用：{response.get('usage', {})}")


if __name__ == "__main__":
    test_baidu_image_understanding()
    test_multi_image_comparison()
