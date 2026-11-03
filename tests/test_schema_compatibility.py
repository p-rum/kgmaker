"""W08 public compatibility acceptance; schema replay never proves population."""
from copy import deepcopy
import pytest
from kgmaker.schema_replay import Replay


def replay_constraint(sql):
    from kgmaker.schema_replay import statements
    replay = Replay(dict(database_id='db', stream_id='main', default_schema='public'))
    replay.evidence = dict(path='V1__base.sql', sha256='a'*64, line=1, statement=1, version='1')
    for tokens, _ in statements(sql):
        replay.apply(tokens)
    return replay


def test_fk_replay_exposes_exact_ordered_local_and_referenced_columns():
    replay = replay_constraint('CREATE TABLE parent (id bigint PRIMARY KEY, alternate bigint UNIQUE); '
        'CREATE TABLE child (id bigint PRIMARY KEY, parent_id bigint, '
        'CONSTRAINT child_parent FOREIGN KEY(parent_id) REFERENCES parent(alternate));')
    fk = replay.get('constraint', ('public','child','child_parent'))
    assert fk['columns'] == ['parent_id']
    assert fk['references'] == ['public','parent']
    assert fk['referenced_columns'] == ['alternate']


def test_wrong_referenced_column_does_not_create_valid_fk():
    replay = replay_constraint('CREATE TABLE parent (id bigint PRIMARY KEY); '
        'CREATE TABLE child (parent_id bigint);')
    before = deepcopy(replay.objects)
    from kgmaker.schema_replay import statements
    from kgmaker.analysis_model import AnalysisError
    tokens = statements('ALTER TABLE child ADD CONSTRAINT bad FOREIGN KEY(parent_id) REFERENCES parent(missing);')[0][0]
    with pytest.raises(AnalysisError):
        replay.apply(tokens)
    assert replay.objects == before


def test_source_only_legacy_mapping_is_unknown_never_available(tmp_path):
    from kgmaker.schema_replay import reconstruct, schema_compatibility
    from kgmaker.scanner import scan_repository
    import subprocess
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    migrations=tmp_path/'db';migrations.mkdir()
    (migrations/'V1__base.sql').write_text('CREATE TABLE orders (id bigint PRIMARY KEY);')
    (tmp_path/'Order.kt').write_text('@Entity @Table(name="orders") class Order { @Column(name="id") val id: Long = 1 }')
    graph=scan_repository(tmp_path)
    schema=reconstruct(tmp_path,dict(database_id='db',stream_id='main',locations=['db'],target='1'))
    before=(deepcopy(graph.to_dict()),deepcopy(schema))
    report=schema_compatibility(schema,graph)
    assert report['status']=='UNKNOWN'
    assert report['deployment_verified'] is False
    assert report['data_availability']=='UNASSESSED'
    assert (graph.to_dict(),schema)==before


@pytest.mark.parametrize('backend',['k1','k2'])
def test_actual_compiler_type_null_decimal_keys_and_later_target_conflict(tmp_path,backend,capsys):
    from kgmaker.schema_replay import schema_compatibility, reconstruct
    from kgmaker.inspection import inspect_jvm, command
    from kgmaker.feature import attach_schema
    from kgmaker.framework import augment_framework_graph
    from kgmaker.store import load_graph
    from kgmaker.worker_protocol import WorkerError
    from test_t015_project_data_resources import jpa_api_jars
    from pathlib import Path
    import os,subprocess
    home=Path(__file__).resolve().parents[1]/'workers'
    try:
        command('jvm',home,kotlin_backend=backend)
        jars=jpa_api_jars()
        stdlib=home/'jvm'/('target-k2' if backend=='k2' else 'target')/'lib/kotlin-stdlib.jar'
        if not stdlib.is_file(): raise WorkerError('pinned stdlib unavailable','TOOLCHAIN_UNAVAILABLE')
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS')=='1':pytest.fail(str(error))
        pytest.skip(str(error))
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    source=tmp_path/'src/main/java/demo/Money.java';source.parent.mkdir(parents=True)
    source.write_text('''package demo;
import jakarta.persistence.*;
@Entity @Table(name="money",schema="public") class Money {
 @Id @Column(name="id",nullable=false) java.lang.Long id;
 @Column(name="amount",nullable=false,precision=12,scale=2,unique=true) java.math.BigDecimal amount;
 @Column(name="custom") BigDecimal custom;
 @Column(name="custom_long") Long customLong;
 @Column(name="custom_string") String customString;
 @Column(name="future") java.lang.Long future;
 @Column(name="label") java.lang.String label;
 @ManyToOne @JoinColumn(name="parent_id",referencedColumnName="id") PropertyMoney parent;
 @ManyToOne @JoinColumn(name="foreign_parent_id",referencedColumnName="id") other.PropertyMoney foreignParent;
 @jakarta.persistence.fake.Column(name="fake") java.lang.Long fakeValue;
 @javax.persistence.Column(name="mixed") java.lang.Long mixedNamespace;
}
class BigDecimal {}
class Long {}
class String {}
@Entity @Table(name="property_money",schema="public") @Access(AccessType.PROPERTY)
class PropertyMoney {
 @Id @Column(name="id",nullable=false) public java.lang.Long getId() { return null; }
}
@MappedSuperclass @Access(AccessType.FIELD) class MoneyBase {
 @Id @Column(name="base_id",nullable=false) protected java.lang.Long baseId;
}
@Entity @Table(name="inherited_money",schema="public") class InheritedMoney extends MoneyBase {}
''')
    foreign=tmp_path/'src/main/java/other/PropertyMoney.java';foreign.parent.mkdir(parents=True)
    foreign.write_text('package other; public class PropertyMoney {}')
    fake=tmp_path/'src/main/java/jakarta/persistence/fake/Column.java';fake.parent.mkdir(parents=True)
    fake.write_text('package jakarta.persistence.fake; public @interface Column { String name(); }')
    mixed=tmp_path/'src/main/java/javax/persistence/Column.java';mixed.parent.mkdir(parents=True)
    mixed.write_text('package javax.persistence; public @interface Column { String name(); }')
    anchor=tmp_path/'src/main/kotlin/demo/Anchor.kt';anchor.parent.mkdir(parents=True)
    anchor.write_text('package demo\nclass Anchor\n')
    migrations=tmp_path/'db';migrations.mkdir()
    (migrations/'V1__base.sql').write_text('CREATE TABLE money (id bigint PRIMARY KEY, amount numeric(12,2) NOT NULL UNIQUE, custom numeric(12,2), custom_long bigint, custom_string varchar(32), future money_domain, label character varying(32), parent_id bigint, foreign_parent_id bigint, fake bigint, mixed bigint); CREATE TABLE property_money(id bigint PRIMARY KEY, alternate bigint UNIQUE); CREATE TABLE inherited_money(base_id bigint PRIMARY KEY); ALTER TABLE money ADD CONSTRAINT money_parent FOREIGN KEY(parent_id) REFERENCES property_money(id);')
    (migrations/'V2__change.sql').write_text('ALTER TABLE money ALTER COLUMN amount TYPE text; ALTER TABLE money RENAME COLUMN id TO old_id; ALTER TABLE money DROP COLUMN custom; ALTER TABLE money DROP CONSTRAINT money_parent; ALTER TABLE money ADD CONSTRAINT money_parent FOREIGN KEY(parent_id) REFERENCES property_money(alternate);')
    (migrations/'V3__missing_fk.sql').write_text('ALTER TABLE money DROP CONSTRAINT money_parent;')
    (migrations/'V4__replace.sql').write_text('ALTER TABLE money DROP COLUMN amount CASCADE; ALTER TABLE money ADD COLUMN amount text;')
    config=dict(database_id='money',stream_id='main',schemas=['public'],default_schema='public',locations=['db'],target='1')
    from kgmaker.analysis_model import write_json
    write_json(tmp_path/'money-config.json',config)
    result=inspect_jvm(tmp_path,home=home,kotlin_backend=backend,classpath=[*jars,str(stdlib)],publish=True,
        build_context=dict(database_id='money',schema_stream_id='main',persistence_schema='public',flyway_target='1'))
    schema=reconstruct(tmp_path,config)
    graph=augment_framework_graph(tmp_path,attach_schema(load_graph(tmp_path),schema,tmp_path),result['context'])
    from unittest.mock import patch
    with patch('subprocess.Popen',side_effect=AssertionError('pure projection must not execute a process')), patch('socket.create_connection',side_effect=AssertionError('pure projection must not connect')):
        report=schema_compatibility(schema,graph,context_id=result['context']['id'])
    amount=next(x for x in report['items'] if x['attribute_name']=='amount')
    assert {k:amount['dimensions'][k]['status'] for k in ('type','nullability','precision','scale','unique')}==dict.fromkeys(('type','nullability','precision','scale','unique'),'COMPATIBLE')
    identifier=next(x for x in report['items'] if x['attribute_name']=='id' and x['compiler_symbol_id'] and 'Money.id:' in x['compiler_symbol_id'])
    assert identifier['dimensions']['primary_key']['status']=='COMPATIBLE'
    assert next(x for x in report['items'] if x['compiler_symbol_id'] and '.PropertyMoney.getId()' in x['compiler_symbol_id'])['dimensions']['type']['status']=='COMPATIBLE'
    inherited=next(x for x in report['items'] if x['attribute_name']=='baseId' and x['table_id'])
    assert inherited['dimensions']['type']['status']=='COMPATIBLE'
    assert report['data_availability']=='UNASSESSED' and report['deployment_verified'] is False
    association=next(x for x in report['items'] if x['attribute_name']=='parent')
    assert association['association_ids'] and association['dimensions']['foreign_key']['status']=='COMPATIBLE'
    assert next(x for x in report['items'] if x['attribute_name']=='foreignParent')['dimensions']['foreign_key']['status']=='UNKNOWN'
    assert all(x['status']=='UNKNOWN' for x in report['items'] if x['attribute_name']=='fakeValue')
    assert all(x['status']=='UNKNOWN' for x in report['items'] if x['attribute_name']=='mixedNamespace')

    custom=next(x for x in report['items'] if x['attribute_name']=='custom')
    assert custom['dimensions']['type']['status']=='UNKNOWN'  # demo.BigDecimal is not java.math.BigDecimal
    for unsupported in ('customLong','customString','future'):
        assert next(x for x in report['items'] if x['attribute_name']==unsupported)['dimensions']['type']['status']=='UNKNOWN'
    assert next(x for x in report['items'] if x['attribute_name']=='label')['dimensions']['type']['status']=='COMPATIBLE'
    for dimension in ('nullable','data_type','constraint'):
        changed=deepcopy(schema)
        if dimension=='constraint':
            key=next(k for k,v in changed['objects'].items() if v['kind']=='constraint' and v.get('constraint_type')=='PRIMARY')
            changed['objects'][key]['columns']=['amount']
        else:
            key=next(k for k,v in changed['objects'].items() if v['kind']=='column' and v['name'][-1]=='amount')
            changed['objects'][key][dimension]=True if dimension=='nullable' else 'text'
        rejected=schema_compatibility(changed,graph,context_id=result['context']['id'])
        assert all(x['status']=='UNKNOWN' for x in rejected['items'])
    from kgmaker.analysis_model import write_json
    from kgmaker.workspace import snapshot_workspace,qualified
    manifest=tmp_path.parent/('workspace-'+backend+'.json')
    write_json(manifest,dict(schema_version=1,workspace_id='money',repositories=[dict(id='money',role='backend',path=tmp_path.name,flyway=[config])],services=[]))
    _,coverage,_,workspace_graph,_=snapshot_workspace(manifest)
    workspace_report=schema_compatibility(coverage['schemas']['money'][0],workspace_graph,context_id=qualified('money',result['context']['id']))
    assert next(x for x in workspace_report['items'] if x['attribute_name']=='amount')['dimensions']['type']['status']=='COMPATIBLE'
    later=reconstruct(tmp_path,{**config,'target':'2'})
    # The context still selects target1: a different supplied target cannot borrow its proof.
    foreign=schema_compatibility(later,graph,context_id=result['context']['id'])
    assert foreign['status']=='UNKNOWN'
    assert all(x['status']!='COMPATIBLE' for x in foreign['items'])
    current=inspect_jvm(tmp_path,home=home,kotlin_backend=backend,classpath=[*jars,str(stdlib)],publish=True,
        build_context=dict(database_id='money',schema_stream_id='main',persistence_schema='public',flyway_target='2'))
    current_graph=augment_framework_graph(tmp_path,attach_schema(load_graph(tmp_path),later,tmp_path),current['context'])
    changed_report=schema_compatibility(later,current_graph,context_id=current['context']['id'])
    assert next(x for x in changed_report['items'] if x['attribute_name']=='amount')['dimensions']['type']['status']=='CONFLICT'
    for absent in ('id','custom'):
        missing=next(x for x in changed_report['items'] if x['compiler_symbol_id'] and x['compiler_symbol_id'].split(':field:',1)[-1]==(identifier if absent=='id' else custom)['compiler_symbol_id'].split(':field:',1)[-1])
        assert missing['dimensions']['presence']['status']=='CONFLICT'
    wrong_fk=next(x for x in changed_report['items'] if x['attribute_name']=='parent')
    assert wrong_fk['dimensions']['foreign_key']['status']=='CONFLICT'
    missing_schema=reconstruct(tmp_path,{**config,'target':'3'})
    missing_context=inspect_jvm(tmp_path,home=home,kotlin_backend=backend,classpath=[*jars,str(stdlib)],publish=True,
        build_context=dict(database_id='money',schema_stream_id='main',persistence_schema='public',flyway_target='3'))
    missing_graph=augment_framework_graph(tmp_path,attach_schema(load_graph(tmp_path),missing_schema,tmp_path),missing_context['context'])
    missing_report=schema_compatibility(missing_schema,missing_graph,context_id=missing_context['context']['id'])
    missing_fk=next(x for x in missing_report['items'] if x['attribute_name']=='parent')
    assert missing_fk['dimensions']['foreign_key']==dict(status='UNKNOWN',reason='NO_PHYSICAL_FK_DECLARED_WITHOUT_EXPLICIT_CONSTRAINT_POLICY')
    from kgmaker.model import KnowledgeGraph
    for member,value in [('nullable',True),('precision',13),('scale',3),('unique',False)]:
        modified=KnowledgeGraph.from_dict(deepcopy(graph.to_dict()))
        symbol=next(x for x in modified.symbols if x['id']==amount['compiler_symbol_id'])
        annotation=next(a for a in symbol['annotations'] if a['name']=='jakarta.persistence.Column')
        annotation['values'][member]=value
        rejected=schema_compatibility(schema,modified,context_id=result['context']['id'])
        assert next(x for x in rejected['items'] if x['attribute_id']==amount['attribute_id'])['status']=='UNKNOWN'
    modified=KnowledgeGraph.from_dict(deepcopy(graph.to_dict()))
    for context in modified.contexts:
        if context['id']==result['context']['id']: context['status']='ERROR'
    assert all(x['status']=='UNKNOWN' for x in schema_compatibility(schema,modified,context_id=result['context']['id'])['items'])
    modified=KnowledgeGraph.from_dict(deepcopy(graph.to_dict()))
    symbol=next(x for x in modified.symbols if x['id']==association['compiler_symbol_id'])
    join=next(a for a in symbol['annotations'] if a['name']=='jakarta.persistence.JoinColumn')
    join['values']['referencedColumnName']='alternate'
    rejected=schema_compatibility(schema,modified,context_id=result['context']['id'])
    assert next(x for x in rejected['items'] if x['attribute_name']=='parent')['status']=='UNKNOWN'
    # The same field/simple name cannot lend another attribute its proof.
    from dataclasses import replace
    original=deepcopy(graph.to_dict())
    project=next(e for e in graph.edges if e.kind=='projects_persistent_attribute' and e.target==amount['attribute_id'])
    other=next(e for e in graph.edges if e.kind=='projects_persistent_attribute' and e.target==identifier['attribute_id'])
    altered=replace(project,source=other.source)
    tampered=replace(graph,edges=[altered if e==project else e for e in graph.edges])
    assert next(x for x in schema_compatibility(schema,tampered,context_id=result['context']['id'])['items'] if x['attribute_name']=='amount')['status']=='UNKNOWN'
    assert graph.to_dict()==original
    from kgmaker.workspace_cli import schema_command
    from types import SimpleNamespace
    real_popen=subprocess.Popen
    def read_only_git(argv,*args,**kwargs):
        assert Path(argv[0]).name=='git',argv
        return real_popen(argv,*args,**kwargs)
    with patch('subprocess.Popen',side_effect=read_only_git),patch('socket.create_connection',side_effect=AssertionError('no network')):
        code=schema_command(SimpleNamespace(root=tmp_path,workspace=None,repo=None,stream='main',target='1',database='money',config='money-config.json',schema_command='compatibility',context=result['context']['id'],format='json'))
    assert code==0
    import json
    cli=json.loads(capsys.readouterr().out)
    assert next(x for x in cli['items'] if x['attribute_name']=='amount')['dimensions']['type']['status']=='COMPATIBLE'
    source.write_text(source.read_text().replace('@Id @Column(name="id",nullable=false) java.lang.Long id;', '@Id @Column(name="old_id",nullable=false) java.lang.Long id;'))
    from kgmaker.scanner import scan_repository
    from kgmaker.graph_provider import retain_compiler_layer
    from kgmaker.store import save_graph
    save_graph(retain_compiler_layer(tmp_path,scan_repository(tmp_path)),tmp_path,generate_docs=False)

    updated=inspect_jvm(tmp_path,home=home,kotlin_backend=backend,classpath=[*jars,str(stdlib)],publish=True,
        build_context=dict(database_id='money',schema_stream_id='main',persistence_schema='public',flyway_target='3'))
    updated_graph=augment_framework_graph(tmp_path,attach_schema(load_graph(tmp_path),missing_schema,tmp_path),updated['context'])
    updated_report=schema_compatibility(missing_schema,updated_graph,context_id=updated['context']['id'])
    updated_id=next(x for x in updated_report['items'] if x['compiler_symbol_id'] and ':field:demo.Money.id:' in x['compiler_symbol_id'])
    assert updated_id['column_id']==identifier['column_id'] and updated_id['dimensions']['type']['status']=='COMPATIBLE'
    # Removing an ancestor migration invalidates positive type/key provenance,
    # even when the latest rename migration is still captured.
    from dataclasses import replace
    uncaptured=replace(updated_graph,files={k:v for k,v in updated_graph.files.items() if k!='db/V1__base.sql'})
    assert all(x['status']=='UNKNOWN' for x in schema_compatibility(missing_schema,uncaptured,context_id=updated['context']['id'])['items'])
    replacement=reconstruct(tmp_path,{**config,'target':'4'})
    replaced=inspect_jvm(tmp_path,home=home,kotlin_backend=backend,classpath=[*jars,str(stdlib)],publish=True,
        build_context=dict(database_id='money',schema_stream_id='main',persistence_schema='public',flyway_target='4'))
    replacement_graph=augment_framework_graph(tmp_path,attach_schema(load_graph(tmp_path),replacement,tmp_path),replaced['context'])
    replacement_report=schema_compatibility(replacement,replacement_graph,context_id=replaced['context']['id'])
    recreated=next(x for x in replacement_report['items'] if x['attribute_name']=='amount')
    assert recreated['column_id']!=amount['column_id'] and ':incarnation:' in recreated['column_id']





def test_explicit_referenced_columns_remain_unknown_when_omitted():
    replay=replay_constraint('CREATE TABLE parent (id bigint PRIMARY KEY); CREATE TABLE child (pid bigint REFERENCES parent);')
    fk=next(x for x in replay.objects.values() if x.get('constraint_type')=='FOREIGN')
    assert fk['referenced_columns'] is None


def test_fk_target_rename_tracks_structured_components_and_drop_fails_closed():
    from kgmaker.schema_replay import statements
    from kgmaker.analysis_model import AnalysisError
    replay=replay_constraint('CREATE TABLE parent (id bigint PRIMARY KEY); CREATE TABLE child (pid bigint REFERENCES parent(id));')
    for tokens,_ in statements('ALTER TABLE parent RENAME COLUMN id TO renamed; ALTER TABLE parent RENAME TO parents;'):
        replay.apply(tokens)
    fk=next(x for x in replay.objects.values() if x.get('constraint_type')=='FOREIGN')
    assert fk['references']==['public','parents'] and fk['referenced_columns']==['renamed']
    before=deepcopy(replay.objects)
    with pytest.raises(AnalysisError): replay.drop('column',('public','parents','renamed'))
    assert replay.objects==before


@pytest.mark.parametrize('version',[1,2,3])
def test_legacy_graph_versions_without_snapshot_proof_remain_unknown(tmp_path,version):
    from kgmaker.model import KnowledgeGraph
    from kgmaker.schema_replay import reconstruct,graph_entities,schema_compatibility
    import subprocess
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    folder=tmp_path/'db';folder.mkdir()
    (folder/'V1__base.sql').write_text('CREATE TABLE money(id bigint PRIMARY KEY);')
    schema=reconstruct(tmp_path,dict(database_id='money',stream_id='main',locations=['db'],target='1'))
    nodes,edges=graph_entities(schema)
    from dataclasses import replace
    legacy_nodes=[replace(n,metadata={k:v for k,v in (n.metadata or {}).items() if k!='schema_snapshot_fingerprint'}) for n in nodes]
    graph=KnowledgeGraph(3,str(tmp_path),'fixture',legacy_nodes,edges,{})
    data=graph.to_dict();data['schema_version']=version
    loaded=KnowledgeGraph.from_dict(data)
    before=deepcopy(loaded.to_dict())
    assert schema_compatibility(schema,loaded)['status']=='UNKNOWN'
    assert loaded.to_dict()==before


def test_invalid_replay_snapshot_does_not_mutate_source_or_last_valid_artifact(tmp_path):
    from kgmaker.model import KnowledgeGraph
    from kgmaker.schema_replay import schema_compatibility
    from kgmaker.analysis_model import AnalysisError
    from unittest.mock import patch
    graph=KnowledgeGraph(3,str(tmp_path),'fixture',[],[],{});before=deepcopy(graph.to_dict())
    source=tmp_path/'source.java';source.write_text('class Source {}')
    artifact=tmp_path/'last-valid.json';artifact.write_text('{"valid":true}')
    files={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with patch('subprocess.Popen',side_effect=AssertionError('no process')),patch('socket.create_connection',side_effect=AssertionError('no network')):
        with pytest.raises(AnalysisError):schema_compatibility({'objects':[], 'config':{}},graph)
    assert graph.to_dict()==before
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()}==files


def test_not_inside_check_is_not_declared_column_nullability():
    replay=replay_constraint('CREATE TABLE notes (id bigint PRIMARY KEY, body text CHECK(body IS NOT NULL));')
    assert replay.get('column',('public','notes','body'))['nullable'] is True


def test_creation_identity_preserves_renamed_objects_and_current_name_components(tmp_path):
    from kgmaker.schema_replay import reconstruct,graph_entities,schema_node_realm
    folder=tmp_path/'db';folder.mkdir()
    (folder/'V1__base.sql').write_text('CREATE SCHEMA IF NOT EXISTS public; CREATE TABLE parent(id bigint PRIMARY KEY); CREATE TABLE child(pid bigint REFERENCES parent(id));')
    (folder/'V2__rename.sql').write_text('ALTER TABLE parent RENAME COLUMN id TO renamed; ALTER TABLE parent RENAME TO parents;')
    (folder/'V3__schema.sql').write_text('ALTER SCHEMA public RENAME TO archive;')
    config=dict(database_id='db',stream_id='main',locations=['db'],schemas=['public','archive'],target='1')
    first=reconstruct(tmp_path,config);original=first['objects']['column:public.parent.id']
    renamed=reconstruct(tmp_path,{**config,'target':'2'})
    current=renamed['objects']['column:public.parents.renamed']
    assert current['id']==original['id']
    assert current['creation_identity']==original['creation_identity']
    assert current['name']==['public','parents','renamed']
    assert 'column:public.parent.id' not in renamed['objects']
    assert all(schema_node_realm(n) for n in graph_entities(renamed)[0] if n.kind in {'db_table','db_column'})
    key=next(x for x in renamed['objects'].values() if x.get('constraint_type')=='PRIMARY')
    fk=next(x for x in renamed['objects'].values() if x.get('constraint_type')=='FOREIGN')
    assert key['columns']==['renamed'] and key['last_change']['version']=='2'
    assert fk['references']==['public','parents'] and fk['referenced_columns']==['renamed']
    archive=reconstruct(tmp_path,{**config,'target':'3'})
    assert archive['status']=='COMPLETE'
    assert all(schema_node_realm(n) for n in graph_entities(archive)[0] if n.kind in {'db_table','db_column'})


def test_drop_recreate_creation_incarnation_and_legacy_metadata_are_not_aliases(tmp_path):
    from kgmaker.schema_replay import reconstruct,graph_entities,schema_node_realm
    from kgmaker.analysis_model import digest
    from dataclasses import replace
    folder=tmp_path/'db';folder.mkdir()
    (folder/'V1__base.sql').write_text('CREATE TABLE money(id bigint PRIMARY KEY);')
    (folder/'V2__replace.sql').write_text('ALTER TABLE money DROP COLUMN id CASCADE; ALTER TABLE money ADD COLUMN id bigint PRIMARY KEY;')
    config=dict(database_id='db',stream_id='main',locations=['db'],target='1')
    first=reconstruct(tmp_path,config);second=reconstruct(tmp_path,{**config,'target':'2'})
    old,new=(s['objects']['column:public.money.id'] for s in (first,second))
    assert old['id']!=new['id']
    assert new['creation_identity']['incarnation']==digest(new['origin'])[:12]
    node=next(n for n in graph_entities(second)[0] if n.kind=='db_column')
    assert schema_node_realm(node)
    legacy=deepcopy(node.metadata);legacy.pop('schema_identity')
    assert schema_node_realm(replace(node,metadata=legacy)) is None
    forged=deepcopy(node.metadata);forged['schema_identity']['incarnation']='a'*12
    forged['schema_identity']['proof_hash']=digest({k:v for k,v in forged['schema_identity'].items() if k!='proof_hash'})
    assert schema_node_realm(replace(node,metadata=forged)) is None
