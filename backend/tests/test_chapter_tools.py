import json
import pytest
from app.db.session import SessionLocal
from app.ai.compose import build_story_prompt

@pytest.mark.asyncio
async def test_priority_and_selected_context(client,proj):
    pid=proj['project']['id'];ch=proj['chapter']['id'];sc=proj['scene']['id']
    base=f'/api/v1/projects/{pid}'
    th=(await client.post(base+'/threads',json={'title':'Required payoff','must_resolve':True,'important':True})).json()
    assert th['must_resolve'] and th['important']
    patched=(await client.patch(base+'/threads/'+th['id'],json={'important':False})).json()
    assert patched['must_resolve'] and not patched['important']
    selections={}
    for key,path,data in [
        ('world','world-entities',{'name':'Chosen world','description':'World reference'}),
        ('locations','locations',{'name':'Chosen location','description':'Location reference'}),
        ('timeline','story-events',{'event_type':'custom','summary':'Chosen event','story_time':42}),
        ('styles','style-profiles',{'name':'Chosen style','instructions':'Style reference'}),
    ]:
        response=await client.post(base+'/'+path,json=data)
        assert response.status_code==200,response.text
        selections[key]=[response.json()['id']]
    url=base+f'/chapters/{ch}/cast'
    assert (await client.put(url,json=selections)).status_code==200
    saved=(await client.put(url,json={'threads':[th['id']]})).json()['cast']
    assert all(saved[k]==v for k,v in selections.items())
    other=(await client.post('/api/v1/projects',json={'name':'Other'})).json()['id']
    foreign=(await client.post(f'/api/v1/projects/{other}/locations',json={'name':'Foreign'})).json()['id']
    assert (await client.put(url,json={'locations':[foreign]})).status_code==422
    async with SessionLocal() as db:
        _,prompt,manifest=await build_story_prompt(db,pid,'writing','Write',scene_id=sc)
        for text in ['World reference','Location reference','Chosen event','Style reference','Required payoff','Hố bắt buộc lấp']:
            assert text in prompt
        assert 'selected world: 1' in manifest
    tree=(await client.get(base+'/manuscript')).json()
    stored=json.loads(next(c for c in tree['chapters'] if c['id']==ch)['cast_json'])
    assert stored['locations']==selections['locations']


@pytest.mark.asyncio
async def test_priority_reminders_survive_normal_limit_and_stop_when_done(client,proj):
    from app.ai.compose import _open_threads_block
    pid=proj['project']['id'];base=f'/api/v1/projects/{pid}'
    for n in range(12):
        await client.post(base+'/threads',json={'title':f'Normal {n}'})
    required=[]
    for n in range(12):
        required.append((await client.post(base+'/threads',json={'title':f'Required {n}','must_resolve':True,'status':'MERGED'})).json())
    async with SessionLocal() as db:
        block,count=await _open_threads_block(db,pid)
        assert count==22
        assert all(th['title'] in block for th in required)
        assert 'không tự đóng hố' in block
    await client.patch(base+'/threads/'+required[0]['id'],json={'status':'RESOLVED'})
    async with SessionLocal() as db:
        block,count=await _open_threads_block(db,pid)
        assert count==21
        assert '- Required 0 [' not in block
