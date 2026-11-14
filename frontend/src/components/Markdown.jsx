import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { linkCitations } from "../utils/markdown";
import CodeBlock from "./CodeBlock";

export default function Markdown({ text, sources, onCite }) {
  const valid = new Set((sources || []).map((s) => s.index));

  const components = {
    a({ href, children }) {
      const m = /^#cite-(\d+)$/.exec(href || "");
      if (m) {
        return (
          <button className="cite" onClick={() => onCite(Number(m[1]))} title="Xem nguồn">
            {children}
          </button>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    img: () => null, // không tải ảnh từ URL do model sinh ra
  };

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {linkCitations(text, valid)}
    </ReactMarkdown>
  );
}