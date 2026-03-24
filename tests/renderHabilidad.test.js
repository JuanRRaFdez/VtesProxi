const { renderHabilidad } = require('../static/assets/icons/renderHabilidad');

describe('renderHabilidad', () => {
  describe('Icon Replacement Logic', () => {
    it('should replace [ACTION] with the correct image span', () => {
      const input = 'Test [ACTION] icon.';
      const output = renderHabilidad(input);
      expect(output).toContain('<img');
      expect(output).toContain('action.png');
    });

    it('should replace [COMBAT] with the correct image span', () => {
      const input = 'Test [COMBAT] icon.';
      const output = renderHabilidad(input);
      expect(output).toContain('<img');
      expect(output).toContain('combat.png');
    });

    it('should handle texts with multiple tags', () => {
      const input = 'Example with [ACTION] and [COMBAT].';
      const output = renderHabilidad(input);
      expect((output.match(/<img/g) || []).length).toBe(2);
      expect(output).toContain('action.png');
      expect(output).toContain('combat.png');
    });

    it('should gracefully ignore unknown tags', () => {
      const input = '[UNKNOWN_TAG] is not replaced.';
      const output = renderHabilidad(input);
      expect(output).toEqual('[UNKNOWN_TAG] is not replaced.');
    });

    it('should handle malformed or incomplete tags', () => {
      const input = 'This is [COMBAT and [ACTION.';
      const output = renderHabilidad(input);
      expect(output).toEqual('This is [COMBAT and [ACTION.');
    });
  });
});