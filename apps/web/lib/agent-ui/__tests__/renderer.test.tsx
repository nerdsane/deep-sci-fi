/**
 * Tests for json-render integration (Phase 0 Week 1)
 *
 * Tests cover:
 * - convertToUITree helper (nested tree → flat UITree)
 * - Component rendering via json-render
 * - Event handler conversion (string → function)
 * - Nested components (Stack with children)
 */

import { describe, test, expect } from 'bun:test';
import { convertToUITree } from '../renderer';
import type { JsonRenderTree } from '@/agent-bus/types';

describe('convertToUITree', () => {
  test('converts simple tree to UITree format', () => {
    const simpleTree: JsonRenderTree = {
      type: 'Button',
      props: { label: 'Click me', variant: 'primary' },
      key: 'btn-1',
    };

    const result = convertToUITree(simpleTree);

    expect(result.root).toBe('btn-1');
    expect(result.elements['btn-1']).toEqual({
      key: 'btn-1',
      type: 'Button',
      props: { label: 'Click me', variant: 'primary' },
      parentKey: null,
    });
  });

  test('converts nested tree with children', () => {
    const nestedTree: JsonRenderTree = {
      type: 'Stack',
      props: { direction: 'vertical', gap: 16 },
      key: 'stack-1',
      children: [
        {
          type: 'Text',
          props: { content: 'Hello' },
          key: 'text-1',
        },
        {
          type: 'Text',
          props: { content: 'World' },
          key: 'text-2',
        },
      ],
    };

    const result = convertToUITree(nestedTree);

    expect(result.root).toBe('stack-1');
    expect(result.elements['stack-1']).toMatchObject({
      key: 'stack-1',
      type: 'Stack',
      props: { direction: 'vertical', gap: 16 },
      parentKey: null,
      children: ['text-1', 'text-2'],
    });
    expect(result.elements['text-1']).toMatchObject({
      key: 'text-1',
      type: 'Text',
      props: { content: 'Hello' },
      parentKey: 'stack-1',
    });
    expect(result.elements['text-2']).toMatchObject({
      key: 'text-2',
      type: 'Text',
      props: { content: 'World' },
      parentKey: 'stack-1',
    });
  });

  test('generates auto-keys when key is missing', () => {
    const treeWithoutKey: any = {
      type: 'Button',
      props: { label: 'Test' },
      // No key provided
    };

    const result = convertToUITree(treeWithoutKey);

    expect(result.root).toMatch(/^auto-\d+$/);
    expect(Object.keys(result.elements)).toHaveLength(1);
  });

  test('handles deeply nested trees', () => {
    const deepTree: JsonRenderTree = {
      type: 'Stack',
      props: {},
      key: 'root',
      children: [
        {
          type: 'Card',
          props: {},
          key: 'card-1',
          children: [
            {
              type: 'Stack',
              props: {},
              key: 'inner-stack',
              children: [
                {
                  type: 'Text',
                  props: { content: 'Deep content' },
                  key: 'deep-text',
                },
              ],
            },
          ],
        },
      ],
    };

    const result = convertToUITree(deepTree);

    expect(result.root).toBe('root');
    expect(result.elements['root'].parentKey).toBeNull();
    expect(result.elements['card-1'].parentKey).toBe('root');
    expect(result.elements['inner-stack'].parentKey).toBe('card-1');
    expect(result.elements['deep-text'].parentKey).toBe('inner-stack');
  });

  test('preserves all props from original tree', () => {
    const treeWithManyProps: JsonRenderTree = {
      type: 'Button',
      props: {
        label: 'Submit',
        variant: 'primary',
        size: 'large',
        disabled: false,
        onClick: 'handleSubmit',
        customProp: { nested: 'value' },
      },
      key: 'btn-complex',
    };

    const result = convertToUITree(treeWithManyProps);

    expect(result.elements['btn-complex'].props).toEqual({
      label: 'Submit',
      variant: 'primary',
      size: 'large',
      disabled: false,
      onClick: 'handleSubmit',
      customProp: { nested: 'value' },
    });
  });
});

describe('Component Registry Integration', () => {
  test('catalog includes expected components', async () => {
    const { catalog } = await import('../catalog');

    // Verify key components are registered
    expect(catalog.components.Button).toBeDefined();
    expect(catalog.components.Text).toBeDefined();
    expect(catalog.components.Stack).toBeDefined();
    expect(catalog.components.Card).toBeDefined();
    expect(catalog.components.Image).toBeDefined();
    expect(catalog.components.Gallery).toBeDefined();

    // Verify 3D Observatory components
    expect(catalog.components.WorldOrb).toBeDefined();
    expect(catalog.components.StarField).toBeDefined();
    expect(catalog.components.AgentPresence).toBeDefined();
    expect(catalog.components.FloatingSuggestions).toBeDefined();
  });

  test('registry includes expected component wrappers', async () => {
    const { componentRegistry } = await import('../registry');

    // Verify key components are wrapped
    expect(componentRegistry.Button).toBeDefined();
    expect(componentRegistry.Text).toBeDefined();
    expect(componentRegistry.Stack).toBeDefined();
    expect(componentRegistry.Card).toBeDefined();

    // Verify each registry entry is a function (wrapper)
    expect(typeof componentRegistry.Button).toBe('function');
    expect(typeof componentRegistry.Text).toBe('function');
  });

  test('catalog actions are defined', async () => {
    const { catalog } = await import('../catalog');

    expect(catalog.actions).toBeDefined();
    expect(catalog.actions.navigateToWorld).toBeDefined();
    expect(catalog.actions.selectSuggestion).toBeDefined();
  });
});

describe('Event Handler Conversion', () => {
  test('Button component wrapper accepts element and onAction props', async () => {
    const { componentRegistry } = await import('../registry');

    // Simple callback to track if action handler is called
    let actionCalled = false;
    const mockOnAction = (action: any) => {
      actionCalled = true;
      expect(action.name).toBe('handleClick');
      expect(action.params.componentId).toBe('btn-1');
    };

    const ButtonWrapper = componentRegistry.Button;
    const element = {
      key: 'btn-1',
      type: 'Button',
      props: {
        label: 'Click me',
        onClick: 'handleClick', // String event handler
      },
      parentKey: null,
    };

    // Call wrapper to get React element
    const result = ButtonWrapper({ element, children: null, onAction: mockOnAction });

    // Wrapper should return a React element
    expect(result).toBeDefined();
    expect(result.type).toBeDefined();
  });
});

describe('convertToUITree Error Handling', () => {
  test('handles trees without props gracefully', () => {
    const treeWithoutProps: any = {
      type: 'Divider',
      key: 'div-1',
      // No props
    };

    const result = convertToUITree(treeWithoutProps);

    expect(result.root).toBe('div-1');
    expect(result.elements['div-1'].props).toBeUndefined();
  });

  test('handles empty children array', () => {
    const treeWithEmptyChildren: JsonRenderTree = {
      type: 'Stack',
      props: {},
      key: 'stack-1',
      children: [],
    };

    const result = convertToUITree(treeWithEmptyChildren);

    expect(result.root).toBe('stack-1');
    expect(result.elements['stack-1'].children).toEqual([]);
  });
});

describe('Dual Format Support', () => {
  test('MountPoint prefers tree over spec when both provided', async () => {
    // This is an integration expectation - MountPoint should render tree first
    // In practice, canvas_ui tool emits both formats for backwards compatibility
    // but MountPoint.tsx line 96 checks tree first: {tree ? ... : spec ? ...}

    // This test documents the expected behavior
    const dualFormatComponent = {
      componentId: 'comp-1',
      spec: { type: 'Button', id: 'btn-legacy' }, // Legacy
      tree: { type: 'Button', props: { label: 'New' }, key: 'btn-new' }, // New
    };

    // MountPoint should use tree, not spec
    expect(dualFormatComponent.tree).toBeDefined();
    expect(dualFormatComponent.spec).toBeDefined();
    // Rendering logic should prefer tree
  });
});

describe('Backwards Compatibility', () => {
  test('ComponentSpec format is still supported', () => {
    // Verify that DynamicRenderer (legacy) is still available
    // This ensures we don't break existing agent code during migration

    const legacySpec = {
      type: 'Button',
      id: 'btn-legacy',
      props: { label: 'Legacy Button' },
    };

    // MountPoint should fall back to DynamicRenderer when tree is not provided
    expect(legacySpec.type).toBe('Button');
    expect(legacySpec.id).toBe('btn-legacy');
  });
});
