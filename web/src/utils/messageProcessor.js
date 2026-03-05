/**
 * 消息处理工具类
 */
export class MessageProcessor {
  /**
   * 将工具结果与消息合并
   * @param {Array} msgs - 消息数组
   * @returns {Array} 合并后的消息数组
   */
  static convertToolResultToMessages(msgs) {
    const toolResponseMap = new Map();

    // 构建工具响应映射
    for (const item of msgs) {
      if (item.type === 'tool' && item.tool_call_id) {
        toolResponseMap.set(item.tool_call_id, item);
      }
    }

    // 合并工具调用和响应
    const convertedMsgs = msgs.map(item => {
      if (item.type === 'ai' && item.tool_calls && item.tool_calls.length > 0) {
        return {
          ...item,
          tool_calls: item.tool_calls.map(toolCall => {
            const toolResponse = toolResponseMap.get(toolCall.id);
            return {
              ...toolCall,
              tool_call_result: toolResponse || null
            };
          })
        };
      }
      return item;
    });

    return convertedMsgs;
  }

  /**
   * 将服务器历史记录转换为对话格式
   * @param {Array} serverHistory - 服务器历史记录
   * @returns {Array} 对话数组
   */
  static convertServerHistoryToMessages(serverHistory) {
    // Filter out standalone 'tool' messages since tool results are already in AI messages' tool_calls
    // Backend new storage: tool results are embedded in AI messages' tool_calls array with tool_call_result field
    const filteredHistory = serverHistory.filter(item => item.type !== 'tool');

    // 按照对话分组
    const conversations = [];
    let currentConv = null;

    for (const item of filteredHistory) {
      if (item.type === 'human') {
        // Start new conversation, finalize previous one
        if (currentConv) {
          // Find the last AI message and mark it as final
          for (let i = currentConv.messages.length - 1; i >= 0; i--) {
            if (currentConv.messages[i].type === 'ai') {
              currentConv.messages[i].isLast = true;
              currentConv.status = 'finished';
              break;
            }
          }
        }
        currentConv = {
          messages: [item],
          status: 'loading'
        };
        conversations.push(currentConv);
      } else if (item.type === 'ai' && currentConv) {
        currentConv.messages.push(item);
      }
    }

    // Mark the last conversation as finished
    if (currentConv && currentConv.messages.length > 0) {
      // Find the last AI message and mark it as final
      for (let i = currentConv.messages.length - 1; i >= 0; i--) {
        if (currentConv.messages[i].type === 'ai') {
          currentConv.messages[i].isLast = true;
          currentConv.status = 'finished';
          break;
        }
      }
    }

    return conversations;
  }

  /**
   * 合并消息块
   * @param {Array} chunks - 消息块数组
   * @returns {Object|null} 合并后的消息
   */
  static mergeMessageChunk(chunks) {
    if (chunks.length === 0) return null;

    // 深拷贝第一个chunk作为结果
    const result = JSON.parse(JSON.stringify(chunks[0]));
    result.content = result.content || '';

    // 合并后续chunks
    for (let i = 1; i < chunks.length; i++) {
      const chunk = chunks[i];

      // 合并内容
      if (chunk.content) {
        result.content += chunk.content;
      }

      // 合并reasoning_content
      if (chunk.reasoning_content) {
        if (!result.reasoning_content) {
          result.reasoning_content = '';
        }
        result.reasoning_content += chunk.reasoning_content;
      }

      // 合并additional_kwargs中的reasoning_content
      if (chunk.additional_kwargs?.reasoning_content) {
        if (!result.additional_kwargs) result.additional_kwargs = {};
        if (!result.additional_kwargs.reasoning_content) {
          result.additional_kwargs.reasoning_content = '';
        }
        result.additional_kwargs.reasoning_content += chunk.additional_kwargs.reasoning_content;
      }

      // 合并tool_calls
      MessageProcessor._mergeToolCalls(result, chunk);
    }

    // 处理AIMessageChunk类型
    if (result.type === 'AIMessageChunk') {
      result.type = 'ai';
      if (result.additional_kwargs?.tool_calls) {
        result.tool_calls = result.additional_kwargs.tool_calls;
      }
    }

    return result;
  }

  /**
   * 合并工具调用
   * @private
   * @param {Object} result - 结果对象
   * @param {Object} chunk - 当前块
   */
  static _mergeToolCalls(result, chunk) {
    if (chunk.additional_kwargs?.tool_calls) {
      if (!result.additional_kwargs) result.additional_kwargs = {};
      if (!result.additional_kwargs.tool_calls) result.additional_kwargs.tool_calls = [];

      for (const toolCall of chunk.additional_kwargs.tool_calls) {
        const existingToolCall = result.additional_kwargs.tool_calls.find(
          t => (t.id === toolCall.id || t.index === toolCall.index)
        );

        if (existingToolCall) {
          // 合并相同ID的tool call
          if (existingToolCall.function && toolCall.function) {
            existingToolCall.function.arguments += toolCall.function.arguments;
          }
        } else {
          // 添加新的tool call
          result.additional_kwargs.tool_calls.push(JSON.parse(JSON.stringify(toolCall)));
        }
      }
    }
  }

  /**
   * 处理流式响应数据块
   * @param {Object} data - 响应数据
   * @param {Object} onGoingConv - 进行中的对话对象
   * @param {Object} state - 状态对象
   * @param {Function} getAgentHistory - 获取历史记录函数
   * @param {Function} handleError - 错误处理函数
   */
  static async processResponseChunk(data, onGoingConv, state, getAgentHistory, handleError) {
    try {
      switch (data.status) {
        case 'init':
          // 代表服务端收到请求并返回第一个响应
          state.waitingServerResponse = false;
          onGoingConv.msgChunks[data.request_id] = [data.msg];
          break;

        case 'loading':
          if (data.msg.id) {
            if (!onGoingConv.msgChunks[data.msg.id]) {
              onGoingConv.msgChunks[data.msg.id] = [];
            }
            onGoingConv.msgChunks[data.msg.id].push(data.msg);
          }
          break;

        case 'error':
          console.error("流式处理出错:", data.message);
          handleError(new Error(data.message), 'stream');
          break;

        case 'finished':
          await getAgentHistory();
          break;

        default:
          console.warn('未知的响应状态:', data.status);
      }
    } catch (error) {
      handleError(error, 'stream');
    }
  }

  /**
   * 为对话消息附加知识库引用信息
   * @param {Array} convList - 对话列�?   * @returns {Array}
   */
  static attachCitationsToConversations(convList) {
    if (!Array.isArray(convList)) return [];

    return convList.map((conv) => {
      if (!conv?.messages) return conv;

      let messagesChanged = false;
      const enrichedMessages = conv.messages.map((msg) => {
        if (!msg || msg.type !== 'ai') return msg;

        const nextCitations = MessageProcessor.extractCitationsFromMessage(msg);
        const hasCitations = nextCitations.length > 0;

        if (!hasCitations) {
          if (!msg.citations || msg.citations.length === 0) return msg;
          messagesChanged = true;
          const { citations: _removed, ...rest } = msg;
          return rest;
        }

        if (MessageProcessor._areCitationsEqual(msg.citations, nextCitations)) {
          return msg;
        }

        messagesChanged = true;
        return { ...msg, citations: nextCitations };
      });

      if (!messagesChanged) return conv;
      return { ...conv, messages: enrichedMessages };
    });
  }

  /**
   * 从单条消息提取引用信息
   * @param {Object} message - 消息对象
   * @returns {Array<Object>}
   */
  static extractCitationsFromMessage(message) {
    if (!message) {
      return [];
    }

    const directCitationCandidates = [];
    if (Array.isArray(message.citations)) {
      directCitationCandidates.push(...message.citations);
    }
    if (Array.isArray(message?.additional_kwargs?.citations)) {
      directCitationCandidates.push(...message.additional_kwargs.citations);
    }
    if (Array.isArray(message?.extra_metadata?.citations)) {
      directCitationCandidates.push(...message.extra_metadata.citations);
    }

    if (directCitationCandidates.length > 0) {
      const normalizedDirectCitations = MessageProcessor._dedupeCitations(
        directCitationCandidates
          .map((item) => {
            if (!item || typeof item !== 'object') return null;
            return MessageProcessor._buildCitation({
              title: item.title || item.name || '',
              path: item.path || item.url || item.source || '',
              snippet: item.snippet || item.content || '',
              score: item.score,
              rerankScore: item.rerankScore || item.rerank_score,
              sourceType: item.sourceType || item.source_type || 'document',
              referenceId: item.referenceId || item.reference_id,
            });
          })
          .filter(Boolean)
      );

      if (normalizedDirectCitations.length > 0) {
        return normalizedDirectCitations.map((item, index) => ({
          ...item,
          index: index + 1,
        }));
      }
    }

    if (!Array.isArray(message.tool_calls) || message.tool_calls.length === 0) {
      return [];
    }

    const references = [];
    const seen = new Set();

    for (const toolCall of message.tool_calls) {
      const rawResult =
        toolCall?.tool_call_result?.content !== undefined
          ? toolCall.tool_call_result.content
          : toolCall?.tool_call_result ?? toolCall?.result;

      if (!rawResult) continue;

      const citations = MessageProcessor._extractCitationsFromToolResult(rawResult);
      if (!Array.isArray(citations) || citations.length === 0) continue;

      citations.forEach((cite) => {
        const key = cite.path || cite.title || cite.referenceId;
        if (!key || seen.has(key)) return;
        seen.add(key);
        references.push(cite);
      });
    }

    return references.map((item, index) => ({
      ...item,
      index: index + 1,
    }));
  }

  /**
   * 解析工具执行结果中的引用信息
   * @param {any} rawResult - 工具执行结果
   * @returns {Array<Object>}
   * @private
   */
  static _extractCitationsFromToolResult(rawResult) {
    if (!rawResult) return [];

    if (typeof rawResult === 'object' && !Array.isArray(rawResult)) {
      return MessageProcessor._extractCitationsFromObject(rawResult);
    }

    if (Array.isArray(rawResult)) {
      return MessageProcessor._extractCitationsFromArray(rawResult);
    }

    if (typeof rawResult !== 'string') return [];

    const trimmed = rawResult.trim();
    if (!trimmed) return [];

    const jsonValue = MessageProcessor._safeJsonParse(trimmed);
    if (jsonValue !== null) {
      return MessageProcessor._extractCitationsFromToolResult(jsonValue);
    }

    if (trimmed.includes('Reference Document List')) {
      return MessageProcessor._parseLightRagReferences(trimmed);
    }

    return [];
  }

  /**
   * 从对象结构提取引用
   * @param {Object} rawResult - 工具结果对象
   * @returns {Array<Object>}
   * @private
   */
  static _extractCitationsFromObject(rawResult) {
    if (!rawResult || typeof rawResult !== 'object' || Array.isArray(rawResult)) return [];

    const collected = [];

    if (rawResult.json !== undefined && rawResult.json !== rawResult) {
      collected.push(...MessageProcessor._extractCitationsFromToolResult(rawResult.json));
    }

    if (Array.isArray(rawResult.content)) {
      const flattened = rawResult.content
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            return item.text || item.content || '';
          }
          return '';
        })
        .filter(Boolean)
        .join('\n');
      collected.push(...MessageProcessor._extractCitationsFromToolResult(flattened));
    }

    if (typeof rawResult.content === 'string' && rawResult.content.includes('Reference Document List')) {
      collected.push(...MessageProcessor._parseLightRagReferences(rawResult.content));
    }

    const metadataSource = typeof rawResult?.metadata?.source === 'string' ? rawResult.metadata.source.trim() : '';
    if (metadataSource) {
      const citation = MessageProcessor._buildCitation({
        title: rawResult.title || metadataSource,
        path: metadataSource,
        snippet: rawResult.snippet || rawResult.content || '',
        score: rawResult.score,
        rerankScore: rawResult.rerank_score,
        sourceType: 'vector',
      });
      if (citation) collected.push(citation);
    }

    const url = typeof rawResult.url === 'string' ? rawResult.url.trim() : '';
    if (url) {
      const citation = MessageProcessor._buildCitation({
        title: rawResult.title || rawResult.name || url,
        path: url,
        snippet: rawResult.snippet || rawResult.content || rawResult.summary || '',
        sourceType: 'web',
      });
      if (citation) collected.push(citation);
    }

    const sourcePath = typeof rawResult.path === 'string'
      ? rawResult.path.trim()
      : (typeof rawResult.source === 'string' ? rawResult.source.trim() : '');
    if (sourcePath) {
      const citation = MessageProcessor._buildCitation({
        title: rawResult.title || rawResult.name || sourcePath.split('/').pop() || sourcePath,
        path: sourcePath,
        snippet: rawResult.snippet || rawResult.content || rawResult.summary || '',
        sourceType: rawResult.sourceType || 'document',
      });
      if (citation) collected.push(citation);
    }

    const nestedArrayFields = [
      'knowledge_base_results',
      'results',
      'references',
      'docs',
      'documents',
      'items',
      'data',
    ];
    nestedArrayFields.forEach((field) => {
      const value = rawResult[field];
      if (value === undefined || value === rawResult) return;
      if (Array.isArray(value) || (value && typeof value === 'object')) {
        collected.push(...MessageProcessor._extractCitationsFromToolResult(value));
      }
    });

    ['knowledge_graph_results', 'result', 'output'].forEach((field) => {
      const value = rawResult[field];
      if (value === undefined || value === rawResult) return;
      if (value && (typeof value === 'object' || typeof value === 'string')) {
        collected.push(...MessageProcessor._extractCitationsFromToolResult(value));
      }
    });

    return MessageProcessor._dedupeCitations(collected);
  }

  /**
   * 从数组结构提取引用
   * @param {Array} rawResult - 工具结果数组
   * @returns {Array<Object>}
   * @private
   */
  static _extractCitationsFromArray(rawResult) {
    if (!Array.isArray(rawResult)) return [];

    const collected = [];

    rawResult.forEach((item) => {
      if (!item) return;

      if (typeof item === 'string') {
        if (item.includes('Reference Document List')) {
          collected.push(...MessageProcessor._parseLightRagReferences(item));
        }
        return;
      }

      if (typeof item !== 'object') return;

      const metadataSource = typeof item?.metadata?.source === 'string' ? item.metadata.source.trim() : '';
      if (metadataSource) {
        const citation = MessageProcessor._buildCitation({
          title: item.title || metadataSource,
          path: metadataSource,
          snippet: item.content || item.snippet || '',
          score: item.score,
          rerankScore: item.rerank_score,
          sourceType: 'vector',
        });
        if (citation) collected.push(citation);
      }

      const url = typeof item.url === 'string' ? item.url.trim() : '';
      if (url) {
        const citation = MessageProcessor._buildCitation({
          title: item.title || item.name || url,
          path: url,
          snippet: item.content || item.snippet || item.summary || '',
          score: item.score,
          rerankScore: item.rerank_score,
          sourceType: 'web',
        });
        if (citation) collected.push(citation);
      }

      const sourcePath = typeof item.path === 'string'
        ? item.path.trim()
        : (typeof item.source === 'string' ? item.source.trim() : '');
      if (sourcePath) {
        const citation = MessageProcessor._buildCitation({
          title: item.title || item.name || sourcePath.split('/').pop() || sourcePath,
          path: sourcePath,
          snippet: item.content || item.snippet || item.summary || '',
          score: item.score,
          rerankScore: item.rerank_score,
          sourceType: item.sourceType || 'document',
        });
        if (citation) collected.push(citation);
      }

      collected.push(...MessageProcessor._extractCitationsFromObject(item));
    });

    return MessageProcessor._dedupeCitations(collected);
  }

  /**
   * 组装标准化引用对象
   * @param {Object} input - 原始引用信息
   * @returns {Object|null}
   * @private
   */
  static _buildCitation(input) {
    if (!input || typeof input !== 'object') return null;

    const path = typeof input.path === 'string' ? input.path.trim() : '';
    const title = typeof input.title === 'string' ? input.title.trim() : '';
    const referenceId = input.referenceId !== undefined ? String(input.referenceId) : '';
    const key = path || title || referenceId;
    if (!key) return null;

    return {
      title: title || (path ? (path.split('/').pop() || path) : ''),
      path: path || '',
      snippet: MessageProcessor._sanitizeSnippet(input.snippet || ''),
      score: input.score,
      rerankScore: input.rerankScore,
      sourceType: input.sourceType || 'document',
      referenceId: referenceId || undefined,
    };
  }

  /**
   * 去重引用列表
   * @param {Array<Object>} citations - 原始引用数组
   * @returns {Array<Object>}
   * @private
   */
  static _dedupeCitations(citations) {
    if (!Array.isArray(citations) || citations.length === 0) return [];

    const seen = new Set();
    const deduped = [];
    citations.forEach((item) => {
      if (!item || typeof item !== 'object') return;
      const key = item.path || item.title || item.referenceId;
      if (!key || seen.has(key)) return;
      seen.add(key);
      deduped.push(item);
    });

    return deduped;
  }

  /**
   * 解析 LightRAG 结果并提取引用列表
   * @param {string} content - 工具输出内容
   * @returns {Array<Object>}
   * @private
   */
  static _parseLightRagReferences(content) {
    if (typeof content !== 'string') return [];

    const referenceBlockMatch = content.match(/Reference Document List[\s\S]*?```([\s\S]*?)```/i);
    if (!referenceBlockMatch) return [];

    const refLines = referenceBlockMatch[1]
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.startsWith('['));

    if (refLines.length === 0) return [];

    const refMap = new Map();
    refLines.forEach((line) => {
      const match = line.match(/^\[(\d+)\]\s+(.*)$/);
      if (!match) return;
      const [, refId, rawPath] = match;
      const title = rawPath.split('/').pop() || rawPath;
      refMap.set(refId, {
        referenceId: refId,
        path: rawPath,
        title,
        snippet: '',
        sourceType: 'lightrag',
      });
    });

    if (refMap.size === 0) return [];

    const chunkBlockMatch = content.match(/Document Chunks[\s\S]*?```json\s*([\s\S]*?)```/i);
    if (chunkBlockMatch) {
      const chunkRaw = chunkBlockMatch[1].trim();
      if (chunkRaw) {
        const sanitized = `[${chunkRaw.replace(/}\s*[\r\n]+\s*{/g, '},{')}]`;
        try {
          const chunks = JSON.parse(sanitized);
          if (Array.isArray(chunks)) {
            chunks.forEach((chunk) => {
              const refId = chunk?.reference_id || chunk?.referenceId;
              if (refId && refMap.has(refId)) {
                const entry = refMap.get(refId);
                if (entry && !entry.snippet) {
                  entry.snippet = MessageProcessor._sanitizeSnippet(chunk.content || '');
                }
              }
            });
          }
        } catch (error) {
          console.debug('Failed to parse LightRAG chunk data:', error);
        }
      }
    }

    return Array.from(refMap.values());
  }

  /**
   * 尝试解析 JSON 字符串
   * @param {string} value - 原始字符串
   * @returns {any|null}
   * @private
   */
  static _safeJsonParse(value) {
    if (typeof value !== 'string') return null;
    const trimmed = value.trim();
    if (!trimmed || (!trimmed.startsWith('{') && !trimmed.startsWith('['))) return null;
    try {
      return JSON.parse(trimmed);
    } catch (error) {
      return null;
    }
  }

  /**
   * 清洗引用内容摘要
   * @param {string} text - 原始文本
   * @param {number} maxLength - 最长长度
   * @returns {string}
   * @private
   */
  static _sanitizeSnippet(text, maxLength = 160) {
    if (!text || typeof text !== 'string') return '';
    const plain = text.replace(/\s+/g, ' ').trim();
    if (plain.length <= maxLength) return plain;
    return `${plain.slice(0, maxLength - 1)}…`;
  }

  /**
   * 判断两个引用列表是否相同
   * @param {Array} current
   * @param {Array} next
   * @returns {boolean}
   * @private
   */
  static _areCitationsEqual(current, next) {
    if (!current && !next) return true;
    if (!Array.isArray(current) || !Array.isArray(next)) return false;
    if (current.length !== next.length) return false;

    return current.every((item, index) => {
      const target = next[index];
      return (
        item?.path === target?.path &&
        item?.title === target?.title &&
        item?.snippet === target?.snippet &&
        item?.sourceType === target?.sourceType
      );
    });
  }

  /**
   * 处理流式响应
   * @param {Response} response - 响应对象
   * @param {Function} processChunk - 处理块的函数
   * @param {Function} scrollToBottom - 滚动到底部函数
   * @param {Function} handleError - 错误处理函数
   */
  static async handleStreamResponse(response, processChunk, scrollToBottom, handleError) {
    try {
      const reader = response.body.getReader();
      let buffer = '';
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留最后一行可能不完整的内容

        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line.trim());
              await processChunk(data);
            } catch (e) {
              console.debug('解析JSON出错:', e.message);
            }
          }
        }
        await scrollToBottom();
      }

      // 处理缓冲区中可能剩余的内容
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer.trim());
          await processChunk(data);
        } catch (e) {
          console.warn('最终缓冲区内容无法解析:', buffer);
        }
      }
    } catch (error) {
      handleError(error, 'stream');
    }
  }
}

export default MessageProcessor;
