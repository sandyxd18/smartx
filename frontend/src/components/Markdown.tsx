import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Exercise statements: CommonMark + GFM tables. Raw HTML is not rendered. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
