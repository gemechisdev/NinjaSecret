#!/usr/bin/env python3
"""
Comprehensive test suite for whisper modifier parsing.
Tests word boundary protection for all modifiers to prevent false positives.
"""

import re
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_whisper_command_test(text: str):
    """
    Test version of parse_whisper_command that can run without full dependencies.
    This mirrors the actual parsing logic in whisper_utils.py
    """
    if not text.strip():
        return None, None, {}

    text = re.sub(r'^@\w+\s+', '', text.strip())

    modifiers = {}

    # All modifier patterns use word boundaries to prevent false positives
    # Word boundary pattern: (?<![a-zA-Z0-9])...(?![a-zA-Z0-9])
    
    # Timer modifier: !timer:N or !t:N (extract first)
    TIMER_PATTERN = r'(?<![a-zA-Z0-9])(!timer|!t):(\d+)(?![a-zA-Z0-9])'
    timer_match = re.search(TIMER_PATTERN, text)
    if timer_match:
        modifiers['timer'] = int(timer_match.group(2))
        text = re.sub(TIMER_PATTERN, '', text).strip()
    
    # Reveal-on-read / Burn after reading modifier
    # Aliases: !reveal, !r, !delete, !del, !d, !burn, !b
    REVEAL_PATTERN = r'(?<![a-zA-Z0-9])(!reveal|!delete|!burn|!del|!r|!d|!b)(?![a-zA-Z0-9])'
    if re.search(REVEAL_PATTERN, text):
        modifiers['reveal_on_read'] = True
        modifiers['burn_after_reading'] = True
        text = re.sub(REVEAL_PATTERN, '', text).strip()

    # VIP style modifier: !vip, !v
    VIP_PATTERN = r'(?<![a-zA-Z0-9])(!vip|!v)(?![a-zA-Z0-9])'
    if re.search(VIP_PATTERN, text):
        modifiers['style'] = 'vip'
        text = re.sub(VIP_PATTERN, '', text).strip()

    # Cute style modifier: !cute, !c, !love, !l
    CUTE_PATTERN = r'(?<![a-zA-Z0-9])(!cute|!love|!c|!l)(?![a-zA-Z0-9])'
    if re.search(CUTE_PATTERN, text):
        modifiers['style'] = 'cute'
        text = re.sub(CUTE_PATTERN, '', text).strip()

    # Simple target extraction for testing
    target_pattern = r'(@[\w]+|[\d]{6,15})\s*$'
    target_match = re.search(target_pattern, text)
    
    if target_match:
        targets_string = target_match.group(1).strip()
        message_content = text[:target_match.start()].strip()
    else:
        return text.strip() if text.strip() else None, None, modifiers

    return message_content if message_content else None, targets_string, modifiers


class TestModifierParsing:
    """Test cases for modifier parsing with word boundaries."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def assert_equal(self, actual, expected, message):
        if actual == expected:
            self.passed += 1
            self.tests.append(('✓', message))
        else:
            self.failed += 1
            self.tests.append(('✗', f"{message}\n     Expected: {expected}\n     Got: {actual}"))

    def assert_true(self, condition, message):
        if condition:
            self.passed += 1
            self.tests.append(('✓', message))
        else:
            self.failed += 1
            self.tests.append(('✗', message))

    def assert_false(self, condition, message):
        if not condition:
            self.passed += 1
            self.tests.append(('✓', message))
        else:
            self.failed += 1
            self.tests.append(('✗', message))

    def assert_not_in(self, substring, string, message):
        if substring not in string:
            self.passed += 1
            self.tests.append(('✓', message))
        else:
            self.failed += 1
            self.tests.append(('✗', f"{message} ('{substring}' found in '{string}')"))

    def run_all_tests(self):
        """Run all test methods."""
        print("=" * 70)
        print("WHISPER MODIFIER PARSING TEST SUITE")
        print("=" * 70)
        
        self.test_reveal_r_detection()
        self.test_reveal_long_form_detection()
        self.test_reveal_false_positives()
        self.test_reveal_content_removal()
        self.test_delete_detection()
        self.test_delete_false_positives()
        self.test_delete_content_removal()
        self.test_vip_detection()
        self.test_vip_false_positives()
        self.test_cute_detection()
        self.test_cute_false_positives()
        self.test_timer_detection()
        self.test_timer_false_positives()
        self.test_short_aliases()
        self.test_combined_modifiers()
        self.test_modifier_positions()
        self.test_edge_cases()
        
        # Print results
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        
        for status, msg in self.tests:
            print(f"  {status} {msg}")
        
        print("\n" + "-" * 70)
        print(f"SUMMARY: {self.passed} passed, {self.failed} failed, {self.passed + self.failed} total")
        print("-" * 70)
        
        return self.failed == 0

    # ==================== !r / !reveal Tests ====================
    
    def test_reveal_r_detection(self):
        """Test !r is correctly detected (now combined with burn_after_reading)."""
        print("\n--- Testing !r detection ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !r")
        self.assert_true(mods.get('reveal_on_read') == True, "!r at end sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!r at end also sets burn_after_reading")
        
        msg, target, mods = parse_whisper_command_test("!r secret message @user")
        self.assert_true(mods.get('reveal_on_read') == True, "!r at start sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!r at start also sets burn_after_reading")
        
        msg, target, mods = parse_whisper_command_test("secret !r message @user")
        self.assert_true(mods.get('reveal_on_read') == True, "!r in middle sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!r in middle also sets burn_after_reading")

    def test_reveal_long_form_detection(self):
        """Test !reveal is correctly detected (now combined with burn_after_reading)."""
        print("\n--- Testing !reveal detection ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !reveal")
        self.assert_true(mods.get('reveal_on_read') == True, "!reveal at end sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!reveal at end also sets burn_after_reading")
        
        msg, target, mods = parse_whisper_command_test("!reveal secret message @user")
        self.assert_true(mods.get('reveal_on_read') == True, "!reveal at start sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!reveal at start also sets burn_after_reading")

    def test_reveal_false_positives(self):
        """Test !r and !reveal don't match in other words."""
        print("\n--- Testing !r/!reveal false positives ---")
        
        msg, target, mods = parse_whisper_command_test("are you !ready yet @user")
        self.assert_false(mods.get('reveal_on_read'), "!ready should NOT match !r")
        
        msg, target, mods = parse_whisper_command_test("!remove this @user")
        self.assert_false(mods.get('reveal_on_read'), "!remove should NOT match !r")
        
        msg, target, mods = parse_whisper_command_test("secret !revealme @user")
        self.assert_false(mods.get('reveal_on_read'), "!revealme should NOT match !reveal")
        
        msg, target, mods = parse_whisper_command_test("pre!r post @user")
        self.assert_false(mods.get('reveal_on_read'), "pre!r should NOT match !r")
        
        msg, target, mods = parse_whisper_command_test("test!reveal @user")
        self.assert_false(mods.get('reveal_on_read'), "test!reveal should NOT match !reveal")

    def test_reveal_content_removal(self):
        """Test !r and !reveal are removed from content."""
        print("\n--- Testing !r/!reveal content removal ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !r")
        self.assert_not_in("!r", msg or "", "!r should be removed from content")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !reveal")
        self.assert_not_in("!reveal", msg or "", "!reveal should be removed from content")
        
        msg, target, mods = parse_whisper_command_test("secret !r message @user")
        self.assert_not_in("!r", msg or "", "!r in middle should be removed from content")

    # ==================== !delete Tests (now alias for !reveal) ====================
    
    def test_delete_detection(self):
        """Test !delete is correctly detected (now alias for !reveal)."""
        print("\n--- Testing !delete detection (alias for !reveal) ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !delete")
        self.assert_true(mods.get('burn_after_reading') == True, "!delete at end sets burn_after_reading")
        self.assert_true(mods.get('reveal_on_read') == True, "!delete at end also sets reveal_on_read")
        
        msg, target, mods = parse_whisper_command_test("!delete secret message @user")
        self.assert_true(mods.get('burn_after_reading') == True, "!delete at start sets burn_after_reading")
        self.assert_true(mods.get('reveal_on_read') == True, "!delete at start also sets reveal_on_read")

    def test_delete_false_positives(self):
        """Test !delete doesn't match in other words."""
        print("\n--- Testing !delete false positives ---")
        
        msg, target, mods = parse_whisper_command_test("!deleteme please @user")
        self.assert_false(mods.get('burn_after_reading'), "!deleteme should NOT match !delete")
        
        msg, target, mods = parse_whisper_command_test("pre!delete post @user")
        self.assert_false(mods.get('burn_after_reading'), "pre!delete should NOT match !delete")
        
        msg, target, mods = parse_whisper_command_test("!deleteall now @user")
        self.assert_false(mods.get('burn_after_reading'), "!deleteall should NOT match !delete")

    def test_delete_content_removal(self):
        """Test !delete is removed from content."""
        print("\n--- Testing !delete content removal ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !delete")
        self.assert_not_in("!delete", msg or "", "!delete should be removed from content")

    # ==================== !vip Tests ====================
    
    def test_vip_detection(self):
        """Test !vip is correctly detected."""
        print("\n--- Testing !vip detection ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !vip")
        self.assert_equal(mods.get('style'), 'vip', "!vip at end sets style to vip")
        
        msg, target, mods = parse_whisper_command_test("!vip secret message @user")
        self.assert_equal(mods.get('style'), 'vip', "!vip at start sets style to vip")

    def test_vip_false_positives(self):
        """Test !vip doesn't match in other words."""
        print("\n--- Testing !vip false positives ---")
        
        msg, target, mods = parse_whisper_command_test("!viponly message @user")
        self.assert_false(mods.get('style') == 'vip', "!viponly should NOT match !vip")
        
        msg, target, mods = parse_whisper_command_test("pre!vip post @user")
        self.assert_false(mods.get('style') == 'vip', "pre!vip should NOT match !vip")

    # ==================== !cute Tests ====================
    
    def test_cute_detection(self):
        """Test !cute is correctly detected."""
        print("\n--- Testing !cute detection ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !cute")
        self.assert_equal(mods.get('style'), 'cute', "!cute at end sets style to cute")
        
        msg, target, mods = parse_whisper_command_test("!cute secret message @user")
        self.assert_equal(mods.get('style'), 'cute', "!cute at start sets style to cute")

    def test_cute_false_positives(self):
        """Test !cute doesn't match in other words."""
        print("\n--- Testing !cute false positives ---")
        
        msg, target, mods = parse_whisper_command_test("!cuteness overload @user")
        self.assert_false(mods.get('style') == 'cute', "!cuteness should NOT match !cute")
        
        msg, target, mods = parse_whisper_command_test("so!cute right @user")
        self.assert_false(mods.get('style') == 'cute', "so!cute should NOT match !cute")

    # ==================== !timer Tests ====================
    
    def test_timer_detection(self):
        """Test !timer:N and !t:N are correctly detected."""
        print("\n--- Testing !timer and !t detection ---")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !timer:3600")
        self.assert_equal(mods.get('timer'), 3600, "!timer:3600 at end sets timer to 3600")
        
        msg, target, mods = parse_whisper_command_test("!timer:60 secret message @user")
        self.assert_equal(mods.get('timer'), 60, "!timer:60 at start sets timer to 60")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !t:3600")
        self.assert_equal(mods.get('timer'), 3600, "!t:3600 at end sets timer to 3600")
        
        msg, target, mods = parse_whisper_command_test("!t:60 secret message @user")
        self.assert_equal(mods.get('timer'), 60, "!t:60 at start sets timer to 60")

    def test_timer_false_positives(self):
        """Test !timer doesn't match in other words."""
        print("\n--- Testing !timer false positives ---")
        
        msg, target, mods = parse_whisper_command_test("!timer:3600extra @user")
        self.assert_false(mods.get('timer'), "!timer:3600extra should NOT match !timer")
        
        msg, target, mods = parse_whisper_command_test("pre!timer:3600 @user")
        self.assert_false(mods.get('timer'), "pre!timer:3600 should NOT match !timer")

    # ==================== Alias Tests ====================
    
    def test_short_aliases(self):
        """Test short aliases for all modifiers."""
        print("\n--- Testing short aliases ---")
        
        # VIP alias !v
        msg, target, mods = parse_whisper_command_test("secret message @user !v")
        self.assert_equal(mods.get('style'), 'vip', "!v sets style to vip")
        
        # Cute aliases !c and !l and !love
        msg, target, mods = parse_whisper_command_test("secret message @user !c")
        self.assert_equal(mods.get('style'), 'cute', "!c sets style to cute")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !l")
        self.assert_equal(mods.get('style'), 'cute', "!l sets style to cute")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !love")
        self.assert_equal(mods.get('style'), 'cute', "!love sets style to cute")
        
        # Reveal/burn aliases !b, !d, !del, !burn
        msg, target, mods = parse_whisper_command_test("secret message @user !b")
        self.assert_true(mods.get('reveal_on_read') == True, "!b sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!b also sets burn_after_reading")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !d")
        self.assert_true(mods.get('reveal_on_read') == True, "!d sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!d also sets burn_after_reading")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !del")
        self.assert_true(mods.get('reveal_on_read') == True, "!del sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!del also sets burn_after_reading")
        
        msg, target, mods = parse_whisper_command_test("secret message @user !burn")
        self.assert_true(mods.get('reveal_on_read') == True, "!burn sets reveal_on_read")
        self.assert_true(mods.get('burn_after_reading') == True, "!burn also sets burn_after_reading")

    # ==================== Combined Modifiers Tests ====================
    
    def test_combined_modifiers(self):
        """Test multiple modifiers work together."""
        print("\n--- Testing combined modifiers ---")
        
        msg, target, mods = parse_whisper_command_test("secret @user !r !vip")
        self.assert_true(mods.get('reveal_on_read') == True, "!r works with !vip")
        self.assert_equal(mods.get('style'), 'vip', "!vip works with !r")
        
        msg, target, mods = parse_whisper_command_test("secret @user !reveal !timer:3600")
        self.assert_true(mods.get('burn_after_reading') == True, "!reveal works with !timer")
        self.assert_equal(mods.get('timer'), 3600, "!timer works with !reveal")
        
        msg, target, mods = parse_whisper_command_test("secret @user !reveal !cute !timer:60")
        self.assert_true(mods.get('reveal_on_read') == True, "!reveal works with multiple mods")
        self.assert_equal(mods.get('style'), 'cute', "!cute works with multiple mods")
        self.assert_equal(mods.get('timer'), 60, "!timer works with multiple mods")

    def test_modifier_positions(self):
        """Test modifiers work in any position."""
        print("\n--- Testing modifier positions ---")
        
        # Start
        msg, target, mods = parse_whisper_command_test("!vip secret message @user")
        self.assert_equal(mods.get('style'), 'vip', "!vip at start works")
        
        # Middle
        msg, target, mods = parse_whisper_command_test("secret !vip message @user")
        self.assert_equal(mods.get('style'), 'vip', "!vip in middle works")
        
        # End
        msg, target, mods = parse_whisper_command_test("secret message @user !vip")
        self.assert_equal(mods.get('style'), 'vip', "!vip at end works")

    def test_edge_cases(self):
        """Test edge cases."""
        print("\n--- Testing edge cases ---")
        
        # Empty input
        msg, target, mods = parse_whisper_command_test("")
        self.assert_equal(mods, {}, "Empty input returns empty modifiers")
        
        # Only whitespace
        msg, target, mods = parse_whisper_command_test("   ")
        self.assert_equal(mods, {}, "Whitespace only returns empty modifiers")
        
        # Multiple of same modifier (should still work)
        msg, target, mods = parse_whisper_command_test("secret !r !r @user")
        self.assert_true(mods.get('reveal_on_read') == True, "Multiple !r still works")
        
        # Both !r and !reveal
        msg, target, mods = parse_whisper_command_test("secret !r !reveal @user")
        self.assert_true(mods.get('reveal_on_read') == True, "Both !r and !reveal work")
        self.assert_not_in("!r", msg or "", "!r removed when both present")
        self.assert_not_in("!reveal", msg or "", "!reveal removed when both present")


def main():
    """Run the test suite."""
    runner = TestModifierParsing()
    success = runner.run_all_tests()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
