#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Domain and IP Converter from ZIP Archive
Converts domain, domain_suffix, and ip_cidr from JSON files in a ZIP archive to payload format
Processes all geosite and geoip files from downloaded ZIP using system wget and unzip
Created on Feb 25, 2025
"""

import json
import os
import shutil
import subprocess
from typing import Dict, List, Union


def download_zip(url: str, output_path: str) -> None:
    """
    使用系统wget下载ZIP文件并保存到指定路径
    
    Args:
        url (str): ZIP文件的URL
        output_path (str): 保存路径
        
    Raises:
        subprocess.CalledProcessError: 如果wget命令失败
        FileNotFoundError: 如果wget不可用
    """
    try:
        subprocess.run(['wget', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"已删除旧文件 {output_path}")
        result = subprocess.run(
            ['wget', url, '-O', output_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"已下载ZIP文件到 {output_path}")
        file_check = subprocess.run(
            ['file', output_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if 'Zip archive data' not in file_check.stdout:
            raise ValueError(f"下载的文件 {output_path} 不是有效的ZIP文件: {file_check.stdout}")
    except FileNotFoundError:
        raise FileNotFoundError("系统未找到wget命令，请确保已安装wget")
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, f"wget下载失败: {e.stderr}"
        )
    except ValueError as e:
        raise e


def extract_zip(zip_path: str, extract_dir: str) -> None:
    """
    使用系统unzip解压ZIP文件到指定目录
    
    Args:
        zip_path (str): ZIP文件路径
        extract_dir (str): 解压目标目录
        
    Raises:
        subprocess.CalledProcessError: 如果unzip命令失败
        FileNotFoundError: 如果unzip不可用
    """
    try:
        subprocess.run(['unzip', '-v'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
            print(f"已清理旧目录 {extract_dir}")
        result = subprocess.run(
            ['unzip', '-o', zip_path, '-d', extract_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"已解压ZIP文件到 {extract_dir}")
    except FileNotFoundError:
        raise FileNotFoundError("系统未找到unzip命令，请确保已安装unzip")
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, f"unzip解压失败: {e.stderr}"
        )


def load_json(file_path: str) -> Dict:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"解析JSON文件 {file_path} 失败: {str(e)}", e.doc, e.pos)


def extract_rules(json_data: Dict) -> Dict[str, List[str]]:
    """
    从JSON数据中提取domain, domain_suffix 和 ip_cidr 列表
    
    Args:
        json_data (dict): 包含rules的JSON数据
        
    Returns:
        dict: 包含domain, domain_suffix, ip_cidr的字典
        
    Raises:
        KeyError: 如果JSON结构不符合预期
    """
    try:
        rules = json_data['rules'][0]
        # 处理 domain_suffix，确保始终返回列表
        domain_suffix = rules.get('domain_suffix', [])
        if isinstance(domain_suffix, str):  # 如果是单个字符串，转换为单元素列表
            domain_suffix = [domain_suffix]
        elif not isinstance(domain_suffix, list):  # 如果不是列表或字符串，设为空列表
            domain_suffix = []
        
        return {
            'domain': rules.get('domain', []),
            'domain_suffix': domain_suffix,
            'ip_cidr': rules.get('ip_cidr', [])
        }
    except (KeyError, IndexError) as e:
        raise KeyError(f"JSON结构错误，无法提取规则列表: {str(e)}")


def format_to_payload(rules: Dict[str, List[str]]) -> str:
    """
    将规则列表格式化为payload字符串
    
    Args:
        rules (dict): 包含domain, domain_suffix, ip_cidr的字典
        
    Returns:
        str: 格式化后的payload字符串
    """
    payload_lines = ["payload:"]
    
    for domain in rules['domain']:
        payload_lines.append(f"  - '{domain}'")
    
    for suffix in rules['domain_suffix']:
        payload_lines.append(f"  - '+.{suffix}'")
    
    for ip in rules['ip_cidr']:
        payload_lines.append(f"  - '{ip}'")
    
    return "\n".join(payload_lines)


def save_to_file(content: str, filename: str) -> None:
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
    except IOError as e:
        raise IOError(f"文件保存失败: {str(e)}")


def process_json_file(json_path: str, output_base_dir: str) -> bool:
    try:
        json_data = load_json(json_path)
        rules = extract_rules(json_data)
        payload_content = format_to_payload(rules)
        filename = os.path.basename(json_path).replace('.json', '')
        if 'geosite' in json_path:
            output_file = os.path.join(output_base_dir, 'geosite', f'site_{filename}.txt')
        elif 'geoip' in json_path:
            output_file = os.path.join(output_base_dir, 'geoip', f'ip_{filename}.txt')
        else:
            output_file = os.path.join(output_base_dir, 'geosite', f'{filename}.txt')
        save_to_file(payload_content, output_file)
        print(f"已处理 {json_path}，保存到 {output_file}")
        return True
    except (json.JSONDecodeError, KeyError, IOError) as e:
        print(f"处理 {json_path} 时出错: {str(e)}")
        return False
    except Exception as e:
        print(f"处理 {json_path} 时发生未知错误: {str(e)}")
        return False


def main():
    zip_url = "https://github.com/vansour/meta-rules/archive/refs/heads/main.zip"
    temp_dir = "temp_extract"
    zip_file = "meta-rules-main.zip"
    output_base_dir = "geo"
    
    try:
        download_zip(zip_url, zip_file)
        extract_zip(zip_file, temp_dir)
        geo_dir = os.path.join(temp_dir, 'meta-rules-main', 'geo')
        if not os.path.exists(geo_dir):
            raise FileNotFoundError("解压后的ZIP文件中未找到meta-rules-main/geo目录")
        
        success_count = 0
        total_count = 0
        
        for subdir in ['geosite', 'geoip']:
            dir_path = os.path.join(geo_dir, subdir)
            if os.path.exists(dir_path):
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith('.json'):
                            json_path = os.path.join(root, file)
                            total_count += 1
                            if process_json_file(json_path, output_base_dir):
                                success_count += 1
        
        print(f"\n处理完成：成功 {success_count}/{total_count} 个文件")
        
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(zip_file):
            os.remove(zip_file)
        print("已清理临时文件")


if __name__ == "__main__":
    main()
