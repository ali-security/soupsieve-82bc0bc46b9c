"""Test attribute selectors."""
import os
import signal
import subprocess
import sys
import soupsieve as sv
from .. import util


class TestAttribute(util.TestCase):
    """Test attribute selectors."""

    MARKUP = """
    <div id="div">
    <p id="0">Some text <span id="1"> in a paragraph</span>.</p>
    <a id="2" href="http://google.com">Link</a>
    <span id="3">Direct child</span>
    <pre id="pre">
    <span id="4">Child 1</span>
    <span id="5">Child 2</span>
    <span id="6">Child 3</span>
    </pre>
    </div>
    """

    def test_attribute_not_equal_no_quotes(self):
        """Test attribute with value that does not equal specified value (no quotes)."""

        # No quotes
        self.assert_selector(
            self.MARKUP,
            'body [id!=\\35]',
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_attribute_not_equal_quotes(self):
        """Test attribute with value that does not equal specified value (quotes)."""

        # Quotes
        self.assert_selector(
            self.MARKUP,
            "body [id!='5']",
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_attribute_not_equal_double_quotes(self):
        """Test attribute with value that does not equal specified value (double quotes)."""

        # Double quotes
        self.assert_selector(
            self.MARKUP,
            'body [id!="5"]',
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def assert_syntax_error_no_timeout(self, pattern, timeout=3):
        """Assert that compiling the pattern fails with a syntax error and does not hang."""

        if hasattr(signal, 'SIGALRM'):

            def timeout_handler(signum, frame):
                raise TimeoutError

            handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

            passed = False
            try:
                with self.assertRaises(sv.SelectorSyntaxError):
                    sv.compile(pattern)
                passed = True
            except TimeoutError:
                pass
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, handler if handler is not None else signal.SIG_DFL)
            self.assertTrue(passed)
        else:
            # `SIGALRM` is not available on all platforms (Windows), so compile the pattern
            # in a child process that is killed if it hangs. Allow extra time for interpreter start-up.
            code = '\n'.join(
                [
                    'import sys',
                    'sys.path.insert(0, {!r})'.format(os.path.dirname(os.path.dirname(os.path.abspath(sv.__file__)))),
                    'import soupsieve as sv',
                    'try:',
                    '    sv.compile({!r})'.format(pattern),
                    'except sv.SelectorSyntaxError:',
                    '    sys.exit(0)',
                    'sys.exit("SelectorSyntaxError was not raised")'
                ]
            )
            try:
                result = subprocess.run(
                    [sys.executable, '-c', code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout * 10
                )
            except subprocess.TimeoutExpired:
                self.fail('Compiling {!r} timed out'.format(pattern))
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))

    def test_bad_attribute_unclused(self):
        """Test bad attribute fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout('[a="' + ('x' * 300))

    def test_bad_attribute_unclosed_single_quote(self):
        """Test bad attribute with an unclosed single quoted value fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout("[a='" + ('x' * 300))

    def test_bad_attribute_unclosed_nested(self):
        """Test bad attribute with an unclosed quoted value in a nested selector fails for syntax error."""

        self.assert_syntax_error_no_timeout('div:is(p, [a="' + ('x' * 300))

    def test_bad_contains_unclosed(self):
        """Test `:-soup-contains` with an unclosed quoted value (shares the value pattern) fails quickly."""

        self.assert_syntax_error_no_timeout('div:-soup-contains("' + ('x' * 300))

    def test_bad_lang_unclosed(self):
        """Test `:lang` with an unclosed quoted value (shares the value pattern) fails quickly."""

        self.assert_syntax_error_no_timeout(":lang('" + ('x' * 300))
