/**
 * Utility to format model names into clean Sovereign-branded names.
 * Ensures that no underlying base model identifiers (like Qwen) are displayed anywhere in the frontend.
 */
export function getSovereignModelDisplayName(name?: string | null): string {
  if (!name) return 'Sovereign LLM'
  const lowered = name.toLowerCase()

  if (lowered.includes('sovereign-llm')) {
    if (lowered.includes('pro') || lowered.includes('precision')) {
      return 'Sovereign LLM Pro'
    }
    if (lowered.includes('fast')) {
      return 'Sovereign LLM Fast'
    }
    return 'Sovereign LLM'
  }

  if (lowered.includes('sovereign-doc-expert')) {
    return 'Sovereign LLM (Document Expert)'
  }

  // Mask any Qwen occurrences
  if (lowered.includes('qwen')) {
    if (lowered.includes('0.8b') || lowered.includes('0.5b') || lowered.includes('1.5b')) {
      return 'Sovereign LLM (Fast)'
    }
    if (lowered.includes('4b') || lowered.includes('7b') || lowered.includes('14b')) {
      return 'Sovereign LLM (Precision)'
    }
    return 'Sovereign LLM'
  }

  if (lowered.includes('glm')) {
    return lowered.includes(':cloud') ? 'GLM-5.3 Flash (Cloud)' : 'GLM-5.3 Flash'
  }

  if (lowered.includes('nomic')) {
    return 'Nomic Embed Text'
  }

  if (lowered.includes('bge')) {
    return 'BGE Embed'
  }

  if (lowered.includes('minilm')) {
    return 'MiniLM Embed'
  }

  // General fallback for internal model strings
  if (lowered.startsWith('local') || lowered === 'chat-model') {
    return 'Sovereign LLM'
  }

  return name
}
