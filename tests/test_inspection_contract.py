from kgmaker.inspection import sanitize


def test_sensitive_headers_urls_and_property_defaults_are_redacted():
    value={'annotations':[{'name':'org.springframework.beans.factory.annotation.Value','values':{'value':'${db.password:literal-secret}'}}],
           'headers':['Authorization=Bearer literal-token','X-Api-Key: literal-key'],
           'url':'https://name:credential@example.test/path?token=literal-url-token&safe=1',
           'password':'literal-password','query':'select x where password = :password'}
    redacted=sanitize(value)
    assert 'literal-' not in str(redacted)
    assert redacted['query']==value['query']
    assert 'safe=1' in redacted['url'] and '[redacted]' in redacted['url']
