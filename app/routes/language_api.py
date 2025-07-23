#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
语言切换API
"""

from flask import Blueprint, request, jsonify, session, make_response
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
language_api = Blueprint('language_api', __name__, url_prefix='/api')

@language_api.route('/change_language', methods=['POST'])
def change_language():
    """
    切换语言设置
    """
    try:
        data = request.json
        if not data or 'language' not in data:
            return jsonify({
                'success': False,
                'error': '缺少语言参数'
            }), 400
        
        language = data['language']
        
        # 验证语言代码
        supported_languages = ['en', 'zh_Hant']
        if language not in supported_languages:
            return jsonify({
                'success': False,
                'error': f'不支持的语言: {language}'
            }), 400
        
        # 设置session
        session['language'] = language
        
        # 创建响应并设置cookie
        response = make_response(jsonify({
            'success': True,
            'language': language,
            'message': '语言设置已更新'
        }))
        
        # 设置cookie，有效期1年
        response.set_cookie('language', language, max_age=31536000, path='/')
        
        logger.info(f"用户切换语言到: {language}")
        
        return response
        
    except Exception as e:
        logger.error(f"切换语言失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"切换语言失败: {str(e)}"
        }), 500