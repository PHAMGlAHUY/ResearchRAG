import CopyButton from "./CopyButton";

function nodeText(node) {
  if (typeof node === "string") return node;
  if (Array.isArray(node)) return node.map(nodeText).join("");
  return node?.props ? nodeText(node.props.children) : "";
}

export default function CodeBlock({ children }) {
  const text = nodeText(children).replace(/\n$/, "");
  return (
    <div className="codeblock">
      <CopyButton text={text} />
      <pre>{children}</pre>
    </div>
  );
}