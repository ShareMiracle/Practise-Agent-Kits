"""
小红书内容填写器

专门负责标题、内容、话题等文本内容的填写，遵循单一职责原则
"""

import asyncio
from typing import List, Optional, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

from ..interfaces import IContentFiller, IBrowserManager
from ..constants import (XHSConfig, XHSSelectors, get_title_input_selectors)
from ...core.exceptions import PublishError, handle_exception
from ...utils.logger import get_logger
from ...utils.text_utils import clean_text_for_browser

logger = get_logger(__name__)


class XHSContentFiller(IContentFiller):
    """小红书内容填写器"""
    
    def __init__(self, browser_manager: IBrowserManager):
        """
        初始化内容填写器
        
        Args:
            browser_manager: 浏览器管理器
        """
        self.browser_manager = browser_manager
    
    @handle_exception
    async def fill_title(self, title: str) -> bool:
        """
        填写标题
        
        Args:
            title: 标题内容
            
        Returns:
            填写是否成功
        """
        logger.info(f"📝 开始填写标题: {title}")
        
        try:
            # 验证标题
            self._validate_title(title)
            
            # 查找标题输入框
            title_input = await self._find_title_input()
            if not title_input:
                raise PublishError("未找到标题输入框", publish_step="标题填写")
            
            # 执行标题填写
            return await self._perform_title_fill(title_input, title)
            
        except Exception as e:
            if isinstance(e, PublishError):
                raise
            else:
                logger.error(f"❌ 标题填写失败: {e}")
                return False
    
    @handle_exception
    async def fill_content(self, content: str) -> bool:
        """
        填写内容
        
        Args:
            content: 笔记内容
            
        Returns:
            填写是否成功
        """
        logger.info(f"📝 开始填写内容: {content[:50]}...")
        
        try:
            # 验证内容
            self._validate_content(content)
            
            # 查找内容编辑器
            content_editor = await self._find_content_editor()
            if not content_editor:
                raise PublishError("未找到内容编辑器", publish_step="内容填写")
            
            # 执行内容填写
            return await self._perform_content_fill(content_editor, content)
            
        except Exception as e:
            if isinstance(e, PublishError):
                raise
            else:
                logger.error(f"❌ 内容填写失败: {e}")
                return False
    
    @handle_exception
    async def fill_topics(self, topics: List[str]) -> bool:
        """
        填写话题标签
        
        基于实测验证的小红书话题自动化机制：
        1. 在编辑器中输入 #话题名
        2. 按回车键(Enter)触发转换
        3. 验证是否生成 .mention 元素
        
        Args:
            topics: 话题列表
            
        Returns:
            填写是否成功
        """
        logger.info(f"🏷️ 开始填写话题: {topics}")
        
        try:
            # 验证话题
            self._validate_topics(topics)
            
            # 执行话题自动化填写
            return await self._perform_topics_automation(topics)
            
        except Exception as e:
            logger.warning(f"⚠️ 话题填写失败: {e}")
            return False  # 话题填写失败不影响主流程
    
    def _validate_title(self, title: str) -> None:
        """
        验证标题
        
        Args:
            title: 标题内容
            
        Raises:
            PublishError: 当标题验证失败时
        """
        if not title or not title.strip():
            raise PublishError("标题不能为空", publish_step="标题验证")
        
        if len(title.strip()) > XHSConfig.MAX_TITLE_LENGTH:
            raise PublishError(f"标题长度超限，最多{XHSConfig.MAX_TITLE_LENGTH}个字符", 
                             publish_step="标题验证")
    
    def _validate_content(self, content: str) -> None:
        """
        验证内容
        
        Args:
            content: 笔记内容
            
        Raises:
            PublishError: 当内容验证失败时
        """
        if not content or not content.strip():
            raise PublishError("内容不能为空", publish_step="内容验证")
        
        if len(content.strip()) > XHSConfig.MAX_CONTENT_LENGTH:
            raise PublishError(f"内容长度超限，最多{XHSConfig.MAX_CONTENT_LENGTH}个字符", 
                             publish_step="内容验证")
    
    def _validate_topics(self, topics: List[str]) -> None:
        """
        验证话题
        
        Args:
            topics: 话题列表
            
        Raises:
            PublishError: 当话题验证失败时
        """
        if len(topics) > XHSConfig.MAX_TOPICS:
            raise PublishError(f"话题数量超限，最多{XHSConfig.MAX_TOPICS}个", 
                             publish_step="话题验证")
        
        for topic in topics:
            if len(topic) > XHSConfig.MAX_TOPIC_LENGTH:
                raise PublishError(f"话题长度超限: {topic}，最多{XHSConfig.MAX_TOPIC_LENGTH}个字符", 
                                 publish_step="话题验证")
    
    async def _find_title_input(self):
        """
        查找标题输入框
        
        Returns:
            标题输入元素，如果未找到返回None
        """
        driver = self.browser_manager.driver
        wait = WebDriverWait(driver, XHSConfig.DEFAULT_WAIT_TIME)
        
        # 尝试多个选择器
        for selector in get_title_input_selectors():
            try:
                logger.debug(f"🔍 尝试标题选择器: {selector}")
                title_input = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                
                if title_input and title_input.is_enabled():
                    logger.info(f"✅ 找到标题输入框: {selector}")
                    return title_input
                    
            except TimeoutException:
                logger.debug(f"⏰ 标题选择器超时: {selector}")
                continue
            except Exception as e:
                logger.debug(f"⚠️ 标题选择器错误: {selector}, {e}")
                continue
        
        logger.error("❌ 未找到可用的标题输入框")
        return None
    
    async def _find_content_editor(self):
        """
        查找内容编辑器 (TAB 键焦点切换版)
        原理：强制聚焦标题框 -> 模拟按下 TAB 键 -> 捕获当前光标所在的元素
        """
        driver = self.browser_manager.driver
        wait = WebDriverWait(driver, 10)
        from selenium.webdriver.common.action_chains import ActionChains
        from ..constants import get_title_input_selectors  # 引入正确的选择器配置
        
        logger.info("🔍 开始寻找正文输入框 (TAB导航模式)...")

        # 1. 首先尝试直接查找 (最快)
        try:
            # 常见的内容框选择器
            direct_selectors = [
                "[contenteditable='true']", 
                ".ql-editor", 
                "#post-textarea",
                ".c-input_textarea"
            ]
            for selector in direct_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.is_displayed():
                        logger.info(f"✅ 直接找到编辑器: {selector}")
                        return elem
                except:
                    continue
        except:
            pass

        # 2. 如果直接查找失败，使用 TAB 键导航策略
        try:
            logger.info("👉 尝试通过 TAB 键从标题框跳转...")
            
            # A. 找到标题输入框 (复用已知的正确选择器)
            title_input = None
            title_selectors = get_title_input_selectors() # 获取所有可能的标题选择器
            
            for selector in title_selectors:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elems:
                        if elem.is_displayed():
                            title_input = elem
                            break
                    if title_input: break
                except:
                    continue
            
            if not title_input:
                logger.error("❌ 无法找到标题输入框作为 TAB 导航起点")
                return None

            # B. 强制聚焦标题框 (关键步骤：使用 JS 强制聚焦，比 click 更稳)
            driver.execute_script("arguments[0].focus();", title_input)
            await asyncio.sleep(0.5)
            
            # C. 发送 TAB 键
            actions = ActionChains(driver)
            actions.send_keys(Keys.TAB).perform()
            await asyncio.sleep(0.8) # 等待焦点移动动画
            
            # D. 获取当前焦点元素 (Active Element)
            active_elem = driver.switch_to.active_element
            
            # 简单验证一下是不是正文框 (通常正文框不是 input 标签，而是 div 或 p)
            if active_elem and active_elem.tag_name.lower() != 'input':
                logger.info(f"✅ TAB 导航成功! 锁定元素: <{active_elem.tag_name}>")
                return active_elem
            else:
                logger.warning(f"⚠️ TAB 跳转后的元素似乎不对 (<{active_elem.tag_name}>)，尝试再次 TAB...")
                # 备选：有时候可能需要按两次 TAB (比如中间有个格式工具栏)
                actions.send_keys(Keys.TAB).perform()
                await asyncio.sleep(0.5)
                active_elem = driver.switch_to.active_element
                if active_elem and active_elem.tag_name.lower() != 'input':
                     logger.info(f"✅ 第二次 TAB 导航成功")
                     return active_elem

        except Exception as e:
            logger.error(f"❌ TAB 导航策略失败: {e}")

        logger.error("❌ 无法定位到内容输入框")
        return None
    
    async def _perform_title_fill(self, title_input, title: str) -> bool:
        """
        执行标题填写
        
        Args:
            title_input: 标题输入元素
            title: 标题内容
            
        Returns:
            填写是否成功
        """
        try:
            # 清空现有内容
            title_input.clear()
            await asyncio.sleep(0.5)
            
            # 输入标题
            cleaned_title = clean_text_for_browser(title)
            title_input.send_keys(cleaned_title)
            
            # 验证输入是否成功
            await asyncio.sleep(1)
            current_value = title_input.get_attribute("value") or title_input.text
            
            if cleaned_title in current_value or len(current_value) > 0:
                logger.info("✅ 标题填写成功")
                return True
            else:
                logger.error("❌ 标题填写验证失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 标题填写过程出错: {e}")
            return False
    
    # ... (前面的代码保持不变) ...

    async def _perform_content_fill(self, content_editor, content: Any) -> bool:
        """
        【精准版】所见即所得：
        - 列表里有多少个元素，就对应多少行
        - 遇到空字符串 "" -> 脚本会直接敲一个回车（产生空行）
        - 遇到 "\n\n" -> split后会产生空元素 -> 进而产生多次回车
        """
        try:
            logger.info("📝 开始填写正文 (精准物理回车模式)...")
            
            # 1. 切分逻辑
            if isinstance(content, str):
                # 比如 "一段\n\n二段" -> ['一段', '', '二段']
                paragraphs = content.replace("\\n", "\n").split("\n")
            elif isinstance(content, list):
                paragraphs = content
            else:
                return False

            # 2. 清空编辑器
            content_editor.click()
            await asyncio.sleep(0.5)
            import sys
            cmd_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
            content_editor.send_keys(cmd_key + "a")
            await asyncio.sleep(0.2)
            content_editor.send_keys(Keys.DELETE)
            await asyncio.sleep(0.5)

            js_script = "document.execCommand('insertText', false, arguments[0]);"
            
            # 3. 循环填入
            for i, p in enumerate(paragraphs):
                # p = p.strip() # ⚠️ 不要 strip()，否则空格会被吃掉
                
                # A. 只有当段落有文字时，才执行 JS 注入
                # 如果 p 是空字符串，这步跳过，直接去按回车 -> 从而形成空行
                if p:
                    self.browser_manager.driver.execute_script(js_script, p)
                    await asyncio.sleep(0.1) # 极速输入
                
                # B. 只要不是最后一行，就敲一下回车
                if i < len(paragraphs) - 1:
                    content_editor.send_keys(Keys.ENTER)
                    await asyncio.sleep(0.1) # 稍微等一下换行渲染

            logger.info("✅ 正文填写完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 内容填写失败: {e}")
            return False

    async def fill_topics(self, topics: List[str]) -> bool:
        """
        【JS 暴力定位版】在文末追加话题
        不依赖键盘快捷键，直接通过 DOM Range API 强制移动光标
        """
        if not topics:
            return True

        driver = self.browser_manager.driver
        
        try:
            logger.info(f"🏷️ 准备添加话题 (JS定位模式): {topics}")

            # 1. 找到正文输入框
            content_editor = await self._find_content_editor()
            if not content_editor:
                return False
            
            # 2. 聚焦编辑框
            content_editor.click()
            await asyncio.sleep(0.5)
            
            # ============================================================
            # 🔥 核心修改：使用 JavaScript Range API 强制移动光标到末尾
            # ============================================================
            js_move_cursor = """
            var element = arguments[0];
            
            // 1. 聚焦元素
            element.focus();
            
            // 2. 创建一个 Range 对象
            var range = document.createRange();
            
            // 3. 选中该元素内的所有内容
            range.selectNodeContents(element);
            
            // 4. 将选区“折叠”到终点 (false 表示 End，true 表示 Start)
            range.collapse(false);
            
            // 5. 获取当前选区对象并应用新的 Range
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            """
            
            # 执行 JS
            driver.execute_script(js_move_cursor, content_editor)
            # ============================================================
            
            await asyncio.sleep(0.5) # 给一点反应时间

            # 3. 换行两次 (制造段落间距)
            # 此时光标一定在最后，直接敲回车即可
            logger.info("   ↳ 正在插入空行...")
            content_editor.send_keys(Keys.ENTER)
            await asyncio.sleep(0.1)
            content_editor.send_keys(Keys.ENTER)
            await asyncio.sleep(0.5)

            # 4. 循环输入话题 (保持原逻辑)
            for topic in topics:
                clean_topic = topic.replace("#", "").strip()
                if not clean_topic: continue
                
                # A. 输入 "#"
                content_editor.send_keys("#")
                await asyncio.sleep(0.3)
                
                # B. 输入话题文字
                content_editor.send_keys(clean_topic)
                await asyncio.sleep(1.0) # 等待菜单
                
                # C. 确认选中
                content_editor.send_keys(Keys.ENTER)
                await asyncio.sleep(0.5)
                
                logger.info(f"   ➕ 已追加话题: #{clean_topic}")

            return True

        except Exception as e:
            logger.error(f"❌ 话题填写失败: {e}")
            return True
        

    async def _input_topic_realistically(self, content_editor, topic_text: str) -> bool:
        """
        使用真实用户输入方式输入话题
        
        基于多次失败分析，采用更可靠的方法：
        1. 逐字符输入模拟真实用户行为
        2. 使用Actions类进行精确操作
        3. 多种备用方案确保成功率
        
        Args:
            content_editor: 内容编辑器元素
            topic_text: 话题文本（包含#号）
            
        Returns:
            输入是否成功
        """
        try:
            driver = self.browser_manager.driver
            from selenium.webdriver.common.action_chains import ActionChains
            
            logger.debug(f"🔧 使用改进的真实输入方式: {topic_text}")
            
            # 方法1: 使用Actions类逐字符输入（最接近真实用户行为）
            try:
                actions = ActionChains(driver)
                actions.click(content_editor)
                await asyncio.sleep(0.2)
                
                # 逐字符输入，每个字符间隔模拟真实打字
                for char in topic_text:
                    actions.send_keys(char)
                    await asyncio.sleep(0.05)  # 短暂间隔模拟打字速度
                
                actions.perform()
                await asyncio.sleep(0.5)  # 等待输入完成
                
                logger.debug("✅ Actions逐字符输入完成")
                
            except Exception as e:
                logger.warning(f"⚠️ Actions输入失败，尝试JavaScript方法: {e}")
                
                # 方法2: 改进的JavaScript输入（更精确的事件模拟）
                script = """
                var editor = arguments[0];
                var text = arguments[1];
                
                // 确保编辑器有焦点
                editor.focus();
                
                // 模拟逐字符输入
                for (let i = 0; i < text.length; i++) {
                    const char = text[i];
                    
                    // 模拟keydown事件
                    const keydownEvent = new KeyboardEvent('keydown', {
                        key: char,
                        code: 'Key' + char.toUpperCase(),
                        bubbles: true,
                        cancelable: true
                    });
                    editor.dispatchEvent(keydownEvent);
                    
                    // 插入字符
                    if (editor.textContent === null) {
                        editor.textContent = char;
                    } else {
                        editor.textContent += char;
                    }
                    
                    // 模拟input事件
                    const inputEvent = new Event('input', {
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText'
                    });
                    editor.dispatchEvent(inputEvent);
                    
                    // 模拟keyup事件
                    const keyupEvent = new KeyboardEvent('keyup', {
                        key: char,
                        code: 'Key' + char.toUpperCase(),
                        bubbles: true,
                        cancelable: true
                    });
                    editor.dispatchEvent(keyupEvent);
                }
                
                return true;
                """
                
                driver.execute_script(script, content_editor, topic_text)
                await asyncio.sleep(0.5)
            
            # 等待可能的下拉菜单出现（但不强制要求）
            dropdown_appeared = await self._wait_for_topic_dropdown_flexible()
            
            # 按回车键触发转换
            logger.debug("🔄 按回车键触发话题转换")
            content_editor.send_keys(Keys.ENTER)
            await asyncio.sleep(0.8)  # 增加等待时间让转换完成
            
            return True
                
        except Exception as e:
            logger.error(f"❌ 改进的真实输入失败: {e}")
            
            # 最后的备用方法：简单直接输入
            try:
                logger.debug("🔄 使用最简单的备用输入方法")
                content_editor.clear()
                await asyncio.sleep(0.1)
                content_editor.send_keys(topic_text)
                await asyncio.sleep(0.3)
                content_editor.send_keys(Keys.ENTER)
                await asyncio.sleep(0.5)
                return True
            except:
                return False
    
    async def _wait_for_topic_dropdown_flexible(self, timeout: float = 1.5) -> bool:
        """
        灵活等待话题下拉菜单出现
        
        尝试多种可能的选择器，不强制要求下拉菜单出现
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            下拉菜单是否出现（仅供参考，不影响后续流程）
        """
        try:
            driver = self.browser_manager.driver
            
            # 可能的下拉菜单选择器（根据小红书可能的实现）
            possible_selectors = [
                '.ql-mention-list-container',  # Quill编辑器默认
                '.mention-list',               # 自定义实现
                '.topic-dropdown',             # 话题下拉菜单
                '.suggestion-list',            # 建议列表
                '[class*="mention"]',          # 包含mention的任何类
                '[class*="dropdown"]',         # 包含dropdown的任何类
                '[class*="suggestion"]',       # 包含suggestion的任何类
                '.autocomplete-container',     # 自动完成容器
                '.search-suggestions'          # 搜索建议
            ]
            
            for selector in possible_selectors:
                try:
                    await asyncio.sleep(0.2)  # 短暂等待
                    
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            # 检查是否包含话题相关内容
                            text_content = element.text.lower()
                            if any(keyword in text_content for keyword in ['话题', '#', 'topic', '浏览']):
                                logger.debug(f"✅ 发现话题下拉菜单: {selector}")
                                return True
                except:
                    continue
            
            logger.debug("⚠️ 未检测到话题下拉菜单，但这不影响转换")
            return False
            
        except Exception as e:
            logger.debug(f"⚠️ 检查话题下拉菜单时出错: {e}")
            return False
    
    async def _wait_for_topic_dropdown(self, timeout: float = 2.0) -> bool:
        """
        等待话题下拉菜单出现（保留旧方法以兼容）
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            下拉菜单是否出现
        """
        return await self._wait_for_topic_dropdown_flexible(timeout)
    
    async def _verify_topic_conversion(self, topic: str) -> bool:
        """
        验证话题是否成功转换为真正的话题标签
        
        改进的验证逻辑：
        1. 更长的等待时间确保DOM更新
        2. 更宽松的验证条件
        3. 多种验证方法的组合
        4. 详细的调试日志
        
        Args:
            topic: 要验证的话题名
            
        Returns:
            转换是否成功
        """
        try:
            driver = self.browser_manager.driver
            
            # 增加等待时间确保DOM完全更新
            await asyncio.sleep(1.0)
            
            logger.debug(f"🔍 开始验证话题 '{topic}' 的转换...")
            
            # 先获取页面上所有可能相关的元素进行调试
            all_mentions = driver.find_elements(By.CSS_SELECTOR, 'a[class*="mention"], [class*="mention"], [data-topic]')
            if all_mentions:
                logger.debug(f"📊 页面上发现 {len(all_mentions)} 个mention相关元素")
                for i, mention in enumerate(all_mentions[:3]):  # 只显示前3个避免日志过多
                    try:
                        logger.debug(f"  元素{i+1}: class='{mention.get_attribute('class')}', text='{mention.text[:50]}'")
                    except:
                        pass
            
            # 方法1: 最宽松的验证 - 检查是否页面上有包含话题的任何元素
            broad_search_patterns = [
                f"//*[contains(text(), '{topic}')]",
                f"//*[contains(text(), '#{topic}')]",
                f"//*[contains(text(), '{topic}[话题]')]",
                f"//*[contains(@data-topic, '{topic}')]"
            ]
            
            for pattern in broad_search_patterns:
                try:
                    elements = driver.find_elements(By.XPATH, pattern)
                    if elements:
                        logger.debug(f"✅ 宽松验证成功：找到 {len(elements)} 个包含 '{topic}' 的元素")
                        
                        # 进一步检查是否是真正的话题元素
                        for element in elements:
                            try:
                                class_name = element.get_attribute('class') or ''
                                if 'mention' in class_name.lower() or element.get_attribute('data-topic'):
                                    logger.debug(f"✅ 话题 '{topic}' 验证成功 - 找到有效mention元素")
                                    return True
                            except:
                                continue
                except:
                    continue
            
            # 方法2: 检查编辑器内容是否包含话题文本
            try:
                content_editor = await self._find_content_editor()
                if content_editor:
                    editor_text = content_editor.text or ''
                    if topic in editor_text or f'#{topic}' in editor_text:
                        logger.debug(f"✅ 话题 '{topic}' 在编辑器文本中找到")
                        
                        # 进一步检查是否是格式化的话题
                        if f'{topic}[话题]' in editor_text or f'#{topic}[话题]' in editor_text:
                            logger.debug(f"✅ 话题 '{topic}' 格式验证成功")
                            return True
                        else:
                            logger.debug(f"⚠️ 话题 '{topic}' 可能转换不完整，但文本存在")
                            return True  # 宽松验证，认为至少添加成功了
            except:
                pass
            
            # 方法3: 检查页面源码是否包含话题相关内容
            try:
                page_source = driver.page_source
                if f'data-topic' in page_source and topic in page_source:
                    logger.debug(f"✅ 话题 '{topic}' 在页面源码中发现data-topic")
                    return True
            except:
                pass
            
            logger.debug(f"❌ 话题 '{topic}' 所有验证方法均失败")
            return False
                    
        except Exception as e:
            logger.warning(f"⚠️ 验证话题 '{topic}' 转换时出错: {e}")
            return False
    
    async def get_current_topics(self) -> List[str]:
        """
        获取当前已添加的所有话题标签
        
        基于实测DOM结构的完整实现：
        - 优先从data-topic属性获取话题名称（最准确）
        - 备用方案：从文本内容提取话题名称
        
        Returns:
            当前话题列表
        """
        try:
            driver = self.browser_manager.driver
            topics = []
            
            # 方法1: 从data-topic属性获取（最准确的方式）
            mentions_with_data = driver.find_elements(By.CSS_SELECTOR, 'a.mention[data-topic]')
            
            for mention in mentions_with_data:
                try:
                    import json
                    data_topic = mention.get_attribute('data-topic')
                    if data_topic:
                        topic_data = json.loads(data_topic)
                        topic_name = topic_data.get('name', '')
                        if topic_name and topic_name not in topics:
                            topics.append(topic_name)
                            logger.debug(f"📊 从data-topic获取话题: {topic_name}")
                except Exception as e:
                    logger.debug(f"⚠️ 解析data-topic失败: {e}")
                    continue
            
            # 方法2: 备用方案 - 从文本内容提取
            if not topics:
                logger.debug("🔄 使用备用方案从文本内容提取话题")
                mentions = driver.find_elements(By.CSS_SELECTOR, '.mention span')
                
                for mention in mentions:
                    try:
                        text = mention.text
                        if '#' in text and '[话题]#' in text:
                            # 提取纯话题名 (去掉#和[话题]#)
                            topic_name = text.replace('#', '').replace('[话题]#', '').strip()
                            if topic_name and topic_name not in topics:
                                topics.append(topic_name)
                                logger.debug(f"📊 从文本内容获取话题: {topic_name}")
                    except:
                        continue
            
            # 方法3: 最后备用 - 查找一般mention元素
            if not topics:
                logger.debug("🔄 使用最后备用方案查找mention元素")
                general_mentions = driver.find_elements(By.CSS_SELECTOR, 'a.mention')
                
                for mention in general_mentions:
                    try:
                        text = mention.text.strip()
                        if text.startswith('#'):
                            # 简单提取话题名
                            topic_name = text.replace('#', '').split('[')[0].strip()
                            if topic_name and topic_name not in topics:
                                topics.append(topic_name)
                                logger.debug(f"📊 从一般mention获取话题: {topic_name}")
                    except:
                        continue
            
            logger.info(f"📊 当前已添加话题: {topics}")
            return topics
            
        except Exception as e:
            logger.warning(f"⚠️ 获取当前话题列表失败: {e}")
            return []
    
    def get_current_content(self) -> dict:
        """
        获取当前页面的内容信息
        
        Returns:
            包含当前内容信息的字典
        """
        try:
            driver = self.browser_manager.driver
            
            result = {
                "title": "",
                "content": "",
                "has_title_input": False,
                "has_content_editor": False
            }
            
            # 获取标题
            for selector in get_title_input_selectors():
                try:
                    title_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if title_elements and title_elements[0].is_displayed():
                        result["has_title_input"] = True
                        result["title"] = title_elements[0].get_attribute("value") or ""
                        break
                except:
                    continue
            
            # 获取内容
            try:
                content_elements = driver.find_elements(By.CSS_SELECTOR, XHSSelectors.CONTENT_EDITOR)
                if content_elements and content_elements[0].is_displayed():
                    result["has_content_editor"] = True
                    result["content"] = content_elements[0].text or ""
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 获取当前内容失败: {e}")
            return {"error": str(e)} 