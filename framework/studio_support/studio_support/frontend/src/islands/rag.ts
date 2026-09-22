import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('rag-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'rag',
      title: 'RAG',
      endpoint: target.dataset.endpoint ?? '/_studio/api/rag/pipelines'
    }
  });
}
