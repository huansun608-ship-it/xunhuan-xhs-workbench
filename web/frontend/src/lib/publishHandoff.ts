import type { PublishDraft } from './store';

/** Extract explicitly labelled copy; keep unstructured replies available for manual editing. */
export function draftFromReply(content: string): PublishDraft {
  const draft: PublishDraft = { title: '', body: content, tags: '', platforms: ['xiaohongshu'], overrides: {}, selectedMedia: [] };
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const label = (line: string) => line.trim().replace(/^#{1,6}\s*/, '').replace(/\*\*/g, '').replace(/[：:]\s*$/, '');
  const titleIndex = lines.findIndex(line => label(line) === '标题');
  const bodyIndex = lines.findIndex((line, i) => i > titleIndex && label(line) === '正文');
  if (titleIndex < 0 || bodyIndex <= titleIndex) return draft;
  const title = lines.slice(titleIndex + 1, bodyIndex).join('\n').trim();
  // Multiple title candidates need human selection; do not guess one.
  if (!title || title.includes('\n')) return draft;
  const endIndex = lines.findIndex((line, i) => i > bodyIndex && (
    /^(话题(?:建议|标签)?|标签|审核备注|审核说明|事实核验|发布建议)$/.test(label(line))
    || /^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)
    || /^(?:#{1,6}\s*)?(?:\*\*)?审核(?:备注|说明)[（(:：]/.test(line.trim())
  ));
  const body = lines.slice(bodyIndex + 1, endIndex < 0 ? undefined : endIndex).join('\n').trim();
  if (!body) return draft;
  draft.title = title;
  draft.body = body;
  const tagsIndex = lines.findIndex((line, i) => i > bodyIndex && /^(话题(?:建议|标签)?|标签)$/.test(label(line)));
  if (tagsIndex >= 0) {
    const tagsLine = lines.slice(tagsIndex + 1).find(line => line.trim());
    draft.tags = [...new Set((tagsLine?.match(/#[^\s#，,]+/g) || []).map(tag => tag.slice(1)))].join(',');
  }
  return draft;
}
