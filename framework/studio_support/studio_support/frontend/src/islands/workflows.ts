import { mount } from 'svelte';
import DAGViewer from '../components/DAGViewer.svelte';

const target = document.getElementById('workflow-island');

if (target) {
  mount(DAGViewer, {
    target,
    props: {
      title: target.dataset.title ?? 'Workflow graph',
      graphEndpoint: target.dataset.graphEndpoint ?? '',
      runsEndpoint: target.dataset.runsEndpoint ?? ''
    }
  });
}
