import React, { useState, useEffect } from 'react';
import { Typography, Card, Space, Tag } from 'antd';
import { CheckCircleFilled, CaretRightOutlined, CopyOutlined, CodeOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

// 打字机效果组件
const TypewriterEffect = ({ content, onComplete }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < content.length) {
      const timer = setTimeout(() => {
        setDisplayedContent((prev) => prev + content[currentIndex]);
        setCurrentIndex((prev) => prev + 1);
      }, 5); // 加快打字速度
      return () => clearTimeout(timer);
    } else {
      if (onComplete) onComplete();
    }
  }, [currentIndex, content, onComplete]);

  return <div style={{ whiteSpace: 'pre-wrap' }}>{displayedContent}</div>;
};

// 高亮数字和百分比
const HighlightNumbers = ({ text }) => {
  if (!text) return null;
  const parts = text.split(/(\d+(?:\.\d+)?%|\d+(?:\.\d+)?)/g);
  return (
    <span>
      {parts.map((part, index) => {
        if (/^\d+(?:\.\d+)?%$/.test(part)) {
          const val = parseFloat(part);
          return (
            <Text key={index} strong style={{ color: '#000', backgroundColor: 'rgba(255,255,0,0.15)', padding: '0 2px', borderRadius: 2 }}>
              {part}
            </Text>
          );
        }
        if (/^\d+(?:\.\d+)?$/.test(part) && parts[index-1] !== ' ' && parts[index+1] !== '.') {
           return <Text key={index} style={{ color: '#4f46e5', fontWeight: 500 }}>{part}</Text>;
        }
        return part;
      })}
    </span>
  );
};

// 代码块组件
const CodeBlock = ({ language, code }) => (
  <div style={{ 
    background: '#1e293b', 
    borderRadius: 8, 
    margin: '16px 0', 
    overflow: 'hidden',
    border: '1px solid #334155'
  }}>
    <div style={{ 
      background: '#0f172a', 
      padding: '8px 16px', 
      display: 'flex', 
      justifyContent: 'space-between',
      alignItems: 'center',
      borderBottom: '1px solid #334155'
    }}>
      <Space>
        <CodeOutlined style={{ color: '#94a3b8' }} />
        <span style={{ color: '#e2e8f0', fontSize: 12, fontFamily: 'monospace' }}>{language || 'text'}</span>
      </Space>
      <CopyOutlined style={{ color: '#94a3b8', cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText(code)} />
    </div>
    <div style={{ padding: 16, overflowX: 'auto' }}>
      <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: 13, color: '#e2e8f0' }}>
        {code}
      </pre>
    </div>
  </div>
);

// 列表渲染器组件
const ListRenderer = ({ items }) => (
  <div style={{ margin: '12px 0 16px 4px' }}>
    {items.map((item, i) => {
      const itemParts = item.split(/(\*\*.*?\*\*)/g);
      return (
        <div key={i} style={{ display: 'flex', marginBottom: 10, fontSize: 14, lineHeight: 1.6 }}>
           <div style={{ 
               minWidth: 22, height: 22, background: '#f1f5f9', color: '#64748b', 
               borderRadius: '6px', fontSize: 11, display: 'flex', 
               alignItems: 'center', justifyContent: 'center',
               marginRight: 12, marginTop: 1, fontWeight: 700,
               border: '1px solid #e2e8f0'
           }}>{i + 1}</div>
           <div style={{ color: '#374151', flex: 1 }}>
               {itemParts.map((part, pi) => {
                   if (part.startsWith('**') && part.endsWith('**')) {
                       return <span key={pi} style={{ fontWeight: 700, color: '#111827' }}><HighlightNumbers text={part.slice(2, -2)} /></span>;
                   }
                   return <HighlightNumbers key={pi} text={part} />;
               })}
           </div>
        </div>
      );
    })}
  </div>
);

// 核心渲染逻辑
const sanitizeContent = (raw) => {
  if (!raw) return raw;
  const lines = raw.split('\n');
  const filtered = lines.filter(line => {
    const trimmed = line.trim();
    if (!trimmed) return true;
    return !/!\[[^\]]*]\(data:image\/png;base64,[^)]*\)/i.test(trimmed);
  });
  return filtered.join('\n');
};

const FormattedContent = ({ content }) => {
  const safeContent = sanitizeContent(content);
  const lines = safeContent.split('\n');
  const elements = [];
  
  let currentList = [];
  let inCodeBlock = false;
  let codeBlockLang = '';
  let codeBlockContent = [];

  lines.forEach((line, index) => {
    const trimmedLine = line.trim();

    // 处理代码块开始/结束
    if (trimmedLine.startsWith('```')) {
      if (inCodeBlock) {
        // 结束代码块
        elements.push(<CodeBlock key={`code-${index}`} language={codeBlockLang} code={codeBlockContent.join('\n')} />);
        inCodeBlock = false;
        codeBlockContent = [];
        return;
      } else {
        // 开始代码块
        // 先清理之前的列表
        if (currentList.length > 0) {
          elements.push(<ListRenderer key={`list-${index}`} items={currentList} />);
          currentList = [];
        }
        inCodeBlock = true;
        codeBlockLang = trimmedLine.slice(3).trim();
        return;
      }
    }

    if (inCodeBlock) {
      codeBlockContent.push(line); // 保留原始缩进
      return;
    }
    
    // 1. 处理标题 (###, ##, #)
    const headerMatch = trimmedLine.match(/^(#{1,4})\s+(.*)/);
    if (headerMatch) {
      if (currentList.length > 0) {
        elements.push(<ListRenderer key={`list-${index}`} items={currentList} />);
        currentList = [];
      }

      const level = headerMatch[1].length;
      const titleText = headerMatch[2].replace(/\*\*/g, '');
      
      const headerStyles = [
        { fontSize: '20px', color: '#111827', marginTop: '24px', marginBottom: '16px' }, 
        { fontSize: '18px', color: '#1f2937', marginTop: '20px', marginBottom: '12px' },
        { fontSize: '16px', color: '#374151', marginTop: '16px', marginBottom: '8px' }, 
        { fontSize: '14px', color: '#4b5563', marginTop: '12px', marginBottom: '4px' }, 
      ];
      
      const style = headerStyles[level - 1] || headerStyles[3];

      elements.push(
        <div key={`header-${index}`} style={{ ...style, fontWeight: 700, display: 'flex', alignItems: 'center' }}>
          {level === 3 && <div style={{ width: 4, height: 16, background: '#4f46e5', marginRight: 8, borderRadius: 2 }} />}
          <HighlightNumbers text={titleText} />
        </div>
      );
      return;
    }

    // 2. 识别结论/答案块
    if (trimmedLine.startsWith('**答案') || trimmedLine.startsWith('答案：') || trimmedLine.startsWith('**结论') || trimmedLine.startsWith('结论：')) {
      if (currentList.length > 0) {
        elements.push(<ListRenderer key={`list-${index}`} items={currentList} />);
        currentList = [];
      }

      const cleanText = trimmedLine.replace(/^(\*\*|)(答案|结论)(：|:)(\*\*|)/, '').trim();
      elements.push(
        <div key={`conclusion-${index}`} style={{ 
          marginTop: 16, marginBottom: 16,
          background: 'linear-gradient(to right, #f0fdf4, #f0fdf4)', 
          border: '1px solid #d1fae5', borderRadius: 12, padding: '16px 20px',
          display: 'flex', gap: 12
        }}>
          <CheckCircleFilled style={{ color: '#10b981', fontSize: 20, marginTop: 2 }} />
          <div>
            <div style={{ fontWeight: 700, color: '#065f46', marginBottom: 4, fontSize: 14 }}>分析结论</div>
            <div style={{ color: '#064e3b', lineHeight: 1.6 }}><HighlightNumbers text={cleanText} /></div>
          </div>
        </div>
      );
      return;
    }

    // 3. 识别列表 (1. 或 -)
    const listMatch = trimmedLine.match(/^(\d+\.|-)\s+(.*)/);
    if (listMatch) {
      currentList.push(listMatch[2]);
      return;
    }

    // 4. 普通文本段落
    if (trimmedLine) {
      if (currentList.length > 0) {
        elements.push(<ListRenderer key={`list-${index}`} items={currentList} />);
        currentList = [];
      }

      const parts = trimmedLine.split(/(\*\*.*?\*\*)/g);
      elements.push(
        <Paragraph key={`p-${index}`} style={{ marginBottom: 12, lineHeight: 1.7, color: '#4b5563' }}>
          {parts.map((part, pi) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <Text key={pi} strong style={{ color: '#111827' }}>{part.slice(2, -2)}</Text>;
            }
            return <HighlightNumbers key={pi} text={part} />;
          })}
        </Paragraph>
      );
    } else if (currentList.length > 0) {
       elements.push(<ListRenderer key={`list-${index}`} items={currentList} />);
       currentList = [];
    }
  });

  if (inCodeBlock) {
     elements.push(<CodeBlock key="code-final" language={codeBlockLang} code={codeBlockContent.join('\n')} />);
  }
  if (currentList.length > 0) {
    elements.push(<ListRenderer key="list-final" items={currentList} />);
  }

  return <div style={{ paddingBottom: 8 }}>{elements}</div>;
};

const MessageRenderer = ({ content, isUser, animate = false, onAnimationComplete }) => {
  const [showFormatted, setShowFormatted] = useState(!animate);

  if (isUser) {
    return <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>;
  }

  if (!showFormatted) {
    return (
      <TypewriterEffect 
        content={content} 
        onComplete={() => {
            setShowFormatted(true);
            if(onAnimationComplete) onAnimationComplete();
        }} 
      />
    );
  }

  return <FormattedContent content={content} />;
};

export default MessageRenderer;
