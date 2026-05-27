import { mount } from 'svelte';
import SchemaForm from '../components/SchemaForm.svelte';

const target = document.getElementById('tool-island');

if (target) {
  mount(SchemaForm, {
    target,
    props: {
      detailEndpoint: target.dataset.detailEndpoint ?? ''
    }
  });
}
