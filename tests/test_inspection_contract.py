from kgmaker.inspection import sanitize


def test_sensitive_headers_urls_and_property_defaults_are_redacted():
    value={'annotations':[{'name':'org.springframework.beans.factory.annotation.Value','values':{'value':'${db.password:literal-secret}'}}],
           'headers':['Authorization=Bearer literal-token','X-Api-Key: literal-key'],
           'url':'https://name:credential@example.test/path?token=literal-url-token&safe=1',
           'password':'literal-password','query':'select x where password = :password'}
    redacted=sanitize(value)
    assert 'literal-' not in str(redacted)
    assert redacted['query']==value['query']
    # HTTP intent never persists URI userinfo, query values or fragments,
    # including parameters whose sensitivity cannot be determined statically.
    assert redacted['url'] == '<redacted-uri>'
    assert 'safe=1' not in str(redacted)
