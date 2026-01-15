-- Emotional Prosody Prompt Templates Seed Data
-- 100 emotionally distinct prompts for voice anchor generation
-- Each prompt: 40-60 words (~15 seconds speech), unambiguous emotional intent

-- Create the table first
CREATE TABLE IF NOT EXISTS prompt_templates (
    template_id TEXT PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    emotion_label TEXT,
    description TEXT,
    exaggeration REAL DEFAULT 0.15,
    cfg_weight REAL DEFAULT 0.8,
    temperature REAL DEFAULT 0.8,
    repetition_penalty REAL DEFAULT 1.2,
    target_valence REAL,
    target_arousal REAL,
    target_tension REAL,
    target_stability REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- POSITIVE - HIGH ENERGY (1-12)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('excited_01', 
'Oh my god, I can''t believe this is actually happening! This is the moment we''ve been waiting for! Everything is falling into place and I am so ready for this. My heart is racing and I just want to jump up and down! This is going to be incredible!', 
'excited', 
'High energy anticipation with physical enthusiasm', 
0.22, 0.9, 1.0, 1.2, 
0.85, 0.95, 0.15, 0.7);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('enthusiastic_01', 
'I absolutely love this idea! Let''s dive right in and make it happen. I''ve got so many thoughts about how we can make this work even better. This is exactly the kind of project that gets me fired up. Count me in completely, let''s do this together!', 
'enthusiastic', 
'Sustained positive energy with eagerness to participate', 
0.2, 0.85, 0.95, 1.2, 
0.8, 0.85, 0.1, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('joyful_01', 
'Everything just feels so wonderfully right today. I woke up with this warmth in my chest and it hasn''t faded. The world seems brighter somehow. I feel genuinely happy, like really truly happy, and I just wanted to share that with you because you matter to me.', 
'joyful', 
'Pure happiness radiating outward, warm and bright', 
0.18, 0.9, 0.9, 1.2, 
0.9, 0.8, 0.05, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('energized_01', 
'I feel so alive right now! Like I could take on anything the world throws at me. My mind is sharp, my body feels ready, and I''ve got this incredible drive pushing me forward. Let''s go do something amazing. I need to move, to create, to make things happen!', 
'energized', 
'Physical and mental vitality, ready for action', 
0.22, 0.85, 1.0, 1.2, 
0.75, 0.9, 0.2, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('exhilarated_01', 
'That was absolutely incredible! My heart is still pounding from the rush. I can feel the adrenaline coursing through me. What an experience! I''m tingling all over and I can''t stop smiling. We have to do that again sometime, that was pure magic!', 
'exhilarated', 
'Post-peak excitement, adrenaline high, physical rush', 
0.25, 0.9, 1.1, 1.2, 
0.85, 0.95, 0.25, 0.6);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('triumphant_01', 
'We did it! Against all the odds, despite everyone who doubted us, we actually pulled it off. This victory is so incredibly sweet. All that hard work, all those late nights, they finally paid off. We proved them wrong. This moment belongs to us!', 
'triumphant', 
'Victory and vindication, proud accomplishment after struggle', 
0.22, 0.95, 0.95, 1.2, 
0.9, 0.9, 0.3, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('proud_01', 
'I have to say, I''m genuinely proud of what we''ve built here. This took real dedication, real sacrifice, and you never gave up. When I look at how far we''ve come, from where we started to where we are now, it fills me with such deep satisfaction. You should feel proud too.', 
'proud', 
'Deep satisfaction in achievement, recognition of effort', 
0.15, 0.85, 0.8, 1.2, 
0.8, 0.7, 0.15, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('confident_01', 
'I know exactly what needs to happen here. Trust me on this one. I''ve seen situations like this before and I know how to handle them. There''s no need to second-guess ourselves. We have the skills, we have the plan, and we have what it takes. Let''s move forward.', 
'confident', 
'Self-assured certainty, calm competence, steady conviction', 
0.12, 0.8, 0.75, 1.2, 
0.6, 0.65, 0.1, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('determined_01', 
'I''m not backing down from this. No matter what obstacles appear, no matter how hard it gets, I''m going to see this through to the end. I''ve made my decision and nothing is going to shake my resolve. This matters too much to quit now. We push forward.', 
'determined', 
'Resolute commitment, unwavering focus on goal', 
0.15, 0.9, 0.85, 1.3, 
0.5, 0.75, 0.4, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('inspired_01', 
'Something just clicked for me. I suddenly see it all so clearly now, how everything connects, what we need to do next. It''s like a fog lifted from my mind. I feel this creative energy flowing through me. The possibilities are endless. We can do something truly special here.', 
'inspired', 
'Creative illumination, visionary clarity, uplifted purpose', 
0.18, 0.85, 0.9, 1.2, 
0.75, 0.8, 0.1, 0.7);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('bold_01', 
'You know what? Let''s just go for it. What''s the worst that could happen? We''ve played it safe for too long. Sometimes you have to take a leap of faith to get where you want to be. I''d rather try and fail than always wonder what if. Let''s make some waves.', 
'bold', 
'Courageous decisiveness, willingness to take risks', 
0.18, 0.85, 0.9, 1.2, 
0.65, 0.8, 0.35, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('amused_01', 
'Ha! That''s actually really funny. I wasn''t expecting that at all. You always manage to catch me off guard with your humor. I needed that laugh today, seriously. You''re absolutely ridiculous sometimes, you know that? In the best possible way, of course.', 
'amused', 
'Genuine laughter, lighthearted enjoyment', 
0.15, 0.8, 0.85, 1.2, 
0.7, 0.7, 0.05, 0.8);

-- ============================================================================
-- POSITIVE - LOW ENERGY (13-20)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('calm_01', 
'Everything is exactly as it should be right now. There''s no rush, no pressure, just this quiet moment of stillness. I can breathe deeply and feel completely at ease. The world can wait. For now, I''m just going to be here, present in this peaceful space, and let everything settle.', 
'calm', 
'Deep tranquility, absence of urgency, centered stillness', 
0.1, 0.75, 0.6, 1.2, 
0.5, 0.2, 0.05, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('peaceful_01', 
'This is nice. Just sitting here with you, not needing to fill the silence with words. There''s something beautiful about these quiet moments we share. No demands, no expectations. Just two people being present together. I feel so at peace right now. Thank you for this.', 
'peaceful', 
'Serene contentment, comfortable silence, gentle presence', 
0.1, 0.75, 0.55, 1.2, 
0.6, 0.15, 0.0, 0.98);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('content_01', 
'I don''t need anything more than what I have right now. Life is good. Maybe not perfect, but genuinely good. I''ve learned to appreciate these simple moments of satisfaction. Not everything has to be extraordinary to be meaningful. Sometimes enough is truly enough, and that''s beautiful.', 
'content', 
'Satisfied acceptance, simple gratitude, quiet happiness', 
0.1, 0.75, 0.6, 1.2, 
0.55, 0.25, 0.05, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('relaxed_01', 
'Mmm, this is exactly what I needed. Just letting all the tension melt away, feeling my shoulders drop, my breathing slow down. Nothing to worry about right now. I can just exist here, comfortable and easy, without any weight on my mind. Pure relaxation.', 
'relaxed', 
'Physical and mental ease, tension release, comfort', 
0.1, 0.7, 0.55, 1.2, 
0.5, 0.2, 0.0, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('grateful_01', 
'I just want you to know how much I appreciate everything you''ve done. It means more to me than I can properly express. You didn''t have to help, but you did, and that kindness hasn''t gone unnoticed. From the bottom of my heart, thank you. I''m truly grateful to have you in my life.', 
'grateful', 
'Deep appreciation, heartfelt thankfulness, warm recognition', 
0.12, 0.8, 0.65, 1.2, 
0.7, 0.35, 0.0, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('relieved_01', 
'Oh thank goodness. I was so worried there for a while, but it''s over now. The weight has lifted off my chest and I can finally breathe again. Everything worked out okay in the end. I feel like I''ve been holding my breath for days and now I can finally exhale. What a relief.', 
'relieved', 
'Release of worry, weight lifted, grateful exhalation', 
0.12, 0.8, 0.7, 1.2, 
0.6, 0.4, 0.1, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('sleepy_01', 
'I''m getting so drowsy. My eyes keep wanting to close. Everything feels soft and heavy right now, like I''m sinking into a warm cloud. Maybe I''ll just rest for a little while. The world can wait until tomorrow. For now, sleep is calling me, and I think I''ll answer.', 
'sleepy', 
'Drowsy heaviness, gentle surrender to rest', 
0.08, 0.7, 0.5, 1.2, 
0.4, 0.1, 0.0, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('dreamlike_01', 
'There''s something almost surreal about this moment. Like we''ve stepped outside of ordinary time somehow. Everything has this soft, hazy quality to it. I''m not entirely sure if this is real or if I''m dreaming. Either way, I don''t want to wake up. Let''s stay here a little longer.', 
'dreamlike', 
'Ethereal, floaty, between waking and sleeping', 
0.1, 0.75, 0.6, 1.2, 
0.5, 0.2, 0.0, 0.6);

-- ============================================================================
-- POSITIVE - INTIMATE/ROMANTIC (21-28)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('affectionate_01', 
'Come here, you. I just want to be close to you right now. You have no idea how much your presence means to me. When you''re near, everything feels warmer somehow. I care about you so deeply. Let me hold you for a while. There''s nowhere else I''d rather be.', 
'affectionate', 
'Warm physical closeness, caring touch, fond attachment', 
0.12, 0.8, 0.7, 1.2, 
0.8, 0.45, 0.05, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('tender_01', 
'Hey. Look at me. You''re beautiful, you know that? Not just on the outside. Everything about you. The way you think, the way you care, the way you see the world. I feel so lucky to know you this way. Let me take care of you tonight. You deserve gentleness.', 
'tender', 
'Gentle adoration, soft protective care, vulnerability accepted', 
0.1, 0.8, 0.65, 1.2, 
0.85, 0.35, 0.0, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('loving_01', 
'I love you. I know I say it often, but I need you to understand how true it is. This feeling I have for you runs deeper than words can reach. You''ve become part of who I am. My heart is yours completely. I didn''t know I could feel this way about another person.', 
'loving', 
'Deep romantic love, emotional commitment, heart-full', 
0.12, 0.85, 0.7, 1.2, 
0.95, 0.5, 0.0, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('nurturing_01', 
'You''ve had such a hard day, haven''t you? Come rest. Let me take care of things for a while. You don''t have to be strong right now. I''m here to support you through this. Lean on me, let yourself be held. I''ve got you, I promise. You''re safe with me.', 
'nurturing', 
'Caretaking warmth, supportive presence, maternal energy', 
0.1, 0.8, 0.6, 1.2, 
0.7, 0.3, 0.0, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('protective_01', 
'I won''t let anyone hurt you. Not if I have anything to say about it. You matter too much to me. Whoever or whatever is causing you pain, we''ll face it together. You''re not alone in this. I''ll stand between you and anything that threatens your peace. That''s a promise.', 
'protective', 
'Fierce caring, defensive love, guardian energy', 
0.15, 0.85, 0.8, 1.2, 
0.65, 0.6, 0.35, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('romantic_01', 
'Do you remember the first time we met? How nervous we both were? I look back at that moment now and think about how far we''ve come together. You''ve changed my life in ways I never expected. Every day with you feels like a gift. I''m falling for you all over again.', 
'romantic', 
'Sentimental intimacy, relationship appreciation, love story', 
0.12, 0.8, 0.7, 1.2, 
0.85, 0.5, 0.05, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('yearning_01', 
'I miss you so much it physically aches. Every moment apart feels like an eternity. I keep thinking about when we''ll be together again, imagining your touch, your voice, your warmth beside me. This distance between us is unbearable. I need you here with me. Please come home soon.', 
'yearning', 
'Aching longing, deep missing, physical need for presence', 
0.15, 0.85, 0.8, 1.2, 
0.4, 0.65, 0.4, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('lustful_01', 
'I want you. Right now. The way you look at me makes my whole body respond. I can barely think straight when you''re this close. My skin is tingling everywhere. I need to feel your hands on me, your breath against my neck. Don''t make me wait any longer.', 
'lustful', 
'Physical desire, arousal, urgent wanting', 
0.2, 0.9, 0.95, 1.2, 
0.7, 0.85, 0.55, 0.7);

-- ============================================================================
-- POSITIVE - SOCIAL/PLAYFUL (29-35)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('playful_01', 
'Bet you can''t catch me! Come on, try! I''m way too quick for you. Oh, you think you''re fast? We''ll see about that! This is so much fun. I haven''t laughed this hard in ages. You''re going down, my friend. Get ready to lose!', 
'playful', 
'Lighthearted fun, childlike energy, games and laughter', 
0.18, 0.8, 0.9, 1.2, 
0.75, 0.8, 0.1, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('teasing_01', 
'Oh really? Is that what you''re going with? That''s adorable. You actually think you''re right about this, don''t you? That''s so cute. I''m just going to sit here and smile while you realize how wrong you are. Take your time, I can wait. This is entertaining.', 
'teasing', 
'Affectionate mockery, light provocation, playful superiority', 
0.15, 0.8, 0.85, 1.2, 
0.6, 0.7, 0.15, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('flirtatious_01', 
'I noticed you looking at me earlier. Do you like what you see? I''ve been thinking about you too, you know. There''s something about you that draws me in. Maybe we should spend some more time together and see where this goes. What do you think?', 
'flirtatious', 
'Coy attraction, playful seduction, romantic interest', 
0.15, 0.85, 0.85, 1.2, 
0.7, 0.65, 0.2, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('mischievous_01', 
'I have an idea, and you''re probably going to tell me it''s a terrible one. But hear me out. No one would ever know it was us. It''s harmless, I promise! Okay, mostly harmless. Come on, live a little! Where''s your sense of adventure? This is going to be hilarious.', 
'mischievous', 
'Troublemaking glee, rule-bending excitement, conspiratorial fun', 
0.18, 0.8, 0.9, 1.2, 
0.6, 0.75, 0.2, 0.7);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('entertained_01', 
'Oh this is good. This is really good. I''m actually enjoying this way more than I expected. Keep going, you have my full attention now. I''m genuinely invested in how this turns out. You''ve got me hooked. I love a good story, and this one is getting interesting.', 
'entertained', 
'Engaged enjoyment, absorbed interest, pleased attention', 
0.12, 0.8, 0.8, 1.2, 
0.65, 0.6, 0.05, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('intrigued_01', 
'Wait, tell me more about that. I hadn''t thought about it from that angle before. This is fascinating. There''s definitely something here worth exploring further. My mind is already racing with questions. What else do you know? I need to understand this better.', 
'intrigued', 
'Intellectual curiosity, captivated interest, wanting more', 
0.12, 0.8, 0.8, 1.2, 
0.55, 0.65, 0.1, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('fascinated_01', 
'This is absolutely remarkable. I''ve never seen anything quite like it before. The complexity, the detail, the way everything interconnects. I could study this for hours and still find new things to appreciate. It''s beautiful in the most profound way. I''m completely captivated.', 
'fascinated', 
'Deep absorption, wonder at complexity, intellectual awe', 
0.15, 0.85, 0.8, 1.2, 
0.7, 0.7, 0.05, 0.85);

-- ============================================================================
-- NEUTRAL - FUNCTIONAL (36-43)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('neutral_01', 
'So here''s the situation as I understand it. We have several options available to us, each with their own advantages and disadvantages. I don''t have a strong preference either way. It really depends on what matters most to you in this case. What would you like to prioritize?', 
'neutral', 
'Emotionally balanced, no particular lean, baseline state', 
0.1, 0.75, 0.7, 1.2, 
0.0, 0.5, 0.3, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('informative_01', 
'Let me explain how this works. The process has three main stages that happen in sequence. First, the initial input is validated. Then it goes through processing where the main transformation occurs. Finally, the output is generated and delivered. Does that make sense so far?', 
'informative', 
'Clear explanation, teaching mode, straightforward delivery', 
0.1, 0.75, 0.7, 1.2, 
0.1, 0.45, 0.15, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('analytical_01', 
'Looking at the data objectively, there are several patterns worth noting. The correlation between these two variables is stronger than expected. However, we should be careful not to confuse correlation with causation here. We''d need more evidence before drawing firm conclusions. Let me break down the numbers.', 
'analytical', 
'Logical examination, evidence-based reasoning, methodical', 
0.08, 0.75, 0.65, 1.2, 
0.05, 0.5, 0.2, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('curious_01', 
'Hmm, that''s interesting. I wonder why that happens. There must be something more to this than what''s on the surface. What if we looked at it from a different perspective? I have so many questions now. Can you tell me more about how this actually works?', 
'curious', 
'Genuine inquiry, open questioning, seeking understanding', 
0.12, 0.8, 0.75, 1.2, 
0.4, 0.6, 0.1, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('contemplative_01', 
'I''ve been thinking about what you said. Turning it over in my mind, looking at it from different angles. There''s wisdom there that I didn''t fully grasp at first. The more I sit with it, the more layers I discover. It''s given me a lot to reflect on.', 
'contemplative', 
'Deep thought, reflective processing, meditative consideration', 
0.08, 0.75, 0.6, 1.2, 
0.3, 0.3, 0.1, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('focused_01', 
'Okay, let''s concentrate on this. I''m blocking out everything else and giving this my full attention. The details matter here, and I don''t want to miss anything important. Walk me through it step by step, and I''ll make sure I understand each part before we move on.', 
'focused', 
'Sharp concentration, undivided attention, task-oriented', 
0.1, 0.8, 0.7, 1.2, 
0.2, 0.6, 0.25, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('patient_01', 
'Take your time. There''s no rush at all. I know this is difficult, and I''m here for however long you need. We can go as slowly as necessary until you feel comfortable. I''m not going anywhere. Whenever you''re ready, we''ll continue together at your pace.', 
'patient', 
'Calm waiting, unhurried support, gentle persistence', 
0.08, 0.75, 0.55, 1.2, 
0.45, 0.25, 0.0, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('understanding_01', 
'I hear you. I really do. What you''re going through makes complete sense given everything that''s happened. Your feelings are valid, and you don''t have to justify them to anyone, least of all me. I may not have all the answers, but I understand why you feel this way.', 
'understanding', 
'Empathetic acknowledgment, validation without judgment', 
0.1, 0.8, 0.65, 1.2, 
0.5, 0.35, 0.05, 0.9);

-- ============================================================================
-- NEUTRAL - SOCIAL (44-50)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('polite_01', 
'Thank you for taking the time to meet with me today. I appreciate your consideration in this matter. If it''s not too much trouble, I''d like to discuss a few points that might be of mutual interest. Please let me know what works best for your schedule.', 
'polite', 
'Courteous formality, social grace, respectful distance', 
0.08, 0.75, 0.65, 1.2, 
0.25, 0.4, 0.1, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('formal_01', 
'Good afternoon. I''m here to present the quarterly findings for your review. The documentation has been prepared according to the established protocols. If there are any questions regarding the methodology or conclusions, I would be happy to address them at the appropriate time.', 
'formal', 
'Professional register, official tone, structured communication', 
0.06, 0.75, 0.6, 1.2, 
0.1, 0.4, 0.2, 0.98);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('diplomatic_01', 
'I can see merit in both perspectives here. Perhaps there''s a way to address everyone''s concerns without anyone having to compromise their core priorities. What if we explored some middle ground options that might satisfy the most important needs on each side?', 
'diplomatic', 
'Tactful mediation, balanced consideration, conflict avoidance', 
0.08, 0.75, 0.65, 1.2, 
0.2, 0.45, 0.15, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('cautious_01', 
'I think we should be careful here. Something about this doesn''t feel quite right to me. Maybe I''m being overly paranoid, but I''d rather we slow down and think this through before committing. What are the potential downsides we might not be seeing?', 
'cautious', 
'Careful hesitation, risk awareness, measured approach', 
0.1, 0.8, 0.7, 1.2, 
0.0, 0.5, 0.4, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('assertive_01', 
'I need to be clear about this. My position is that we proceed as I''ve outlined. I''ve considered the alternatives and this is the right course of action. I respect your input, but ultimately this is my decision to make. Let''s move forward with the plan.', 
'assertive', 
'Firm but respectful, clear boundaries, confident leadership', 
0.12, 0.85, 0.75, 1.2, 
0.3, 0.65, 0.35, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('matter-of-fact_01', 
'Here''s the situation. The deadline is in two weeks. We have three tasks remaining. The resources are limited but adequate if we distribute them properly. These are the facts. Now we need to decide how to proceed based on what we know.', 
'matter-of-fact', 
'Straightforward statements, no embellishment, reality-focused', 
0.06, 0.75, 0.65, 1.2, 
0.0, 0.45, 0.2, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('detached_01', 
'It doesn''t really affect me either way. I can observe the situation objectively without being invested in the outcome. Whatever happens, happens. I''m simply here to provide information, not to influence the direction. The choice is entirely yours to make.', 
'detached', 
'Emotional distance, uninvested observation, separated stance', 
0.06, 0.7, 0.6, 1.2, 
0.0, 0.3, 0.1, 0.95);

-- ============================================================================
-- NEGATIVE - HIGH INTENSITY (51-60)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('angry_01', 
'This is completely unacceptable! How could you let this happen? I trusted you with this responsibility and you let me down. I am so frustrated right now. We had an agreement and you just threw it away. Do you have any idea how much damage this has caused?', 
'angry', 
'Hot frustration, controlled but intense anger, disappointment wrath', 
0.2, 0.95, 1.0, 1.3, 
-0.7, 0.85, 0.85, 0.7);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('furious_01', 
'I cannot believe what I''m hearing! This is outrageous! Every single line was crossed and you just stood there and let it happen! I have never been this angry in my entire life! Someone is going to answer for this disaster! This is absolutely inexcusable!', 
'furious', 
'Explosive rage, volcanic intensity, beyond control', 
0.28, 1.0, 1.2, 1.3, 
-0.9, 0.98, 0.95, 0.4);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('frustrated_01', 
'I just can''t get this to work no matter what I try! Every time I think I''ve solved the problem, another one pops up. This is so aggravating! I''ve been at this for hours and I''m getting nowhere. Why does everything have to be so difficult? I''m at my wit''s end here.', 
'frustrated', 
'Blocked progress, repeated failure, mounting irritation', 
0.18, 0.9, 0.95, 1.2, 
-0.5, 0.8, 0.75, 0.65);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('irritated_01', 
'Could you please stop doing that? It''s really getting on my nerves. I''ve asked you nicely already and you''re still at it. This constant interruption is making it impossible to concentrate. I''m trying very hard to stay calm here but you''re making it difficult.', 
'irritated', 
'Low-grade anger, annoyance, patience wearing thin', 
0.15, 0.85, 0.85, 1.2, 
-0.4, 0.65, 0.6, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('outraged_01', 
'How dare they! This is a violation of everything we stand for! People should be held accountable for actions like this. I refuse to accept this kind of behavior in any form. This injustice cannot be allowed to stand. Someone has to speak up and I will not be silent!', 
'outraged', 
'Righteous anger, moral fury, principle-driven rage', 
0.22, 0.95, 1.0, 1.2, 
-0.6, 0.9, 0.9, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('defiant_01', 
'No. Absolutely not. I refuse. You can threaten me all you want but I will not comply with this. I know what''s right and I''m going to stand my ground no matter what the consequences are. You can''t make me do something I fundamentally disagree with. Try me.', 
'defiant', 
'Stubborn resistance, rebellious stance, refusing submission', 
0.18, 0.9, 0.9, 1.3, 
-0.3, 0.8, 0.8, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('bitter_01', 
'Of course. Of course this happened. Why would I expect anything different? Everything I work for just turns to dust eventually. I should have known better than to hope for a different outcome. The universe seems determined to prove me right about expecting the worst.', 
'bitter', 
'Cynical hurt, accumulated disappointment, sour resignation', 
0.12, 0.85, 0.8, 1.2, 
-0.6, 0.5, 0.65, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('resentful_01', 
'I haven''t forgotten what happened. And honestly, I don''t think I can just move past it. Every time I see them, it all comes flooding back. They got away with it while I suffered the consequences. That kind of unfairness doesn''t just disappear. It sits here inside me.', 
'resentful', 
'Held grudge, festering injustice, lingering hurt', 
0.12, 0.85, 0.8, 1.2, 
-0.65, 0.55, 0.7, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('disgusted_01', 
'That is absolutely revolting. I can''t even look at it. The very thought makes my stomach turn. How can anyone think this is acceptable? I need to get away from this right now. This is deeply offensive to everything I believe in. Get it away from me.', 
'disgusted', 
'Physical revulsion, moral repulsion, visceral rejection', 
0.18, 0.9, 0.9, 1.2, 
-0.8, 0.75, 0.8, 0.75);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('contemptuous_01', 
'You actually think that was impressive? Please. I''ve seen better work from complete beginners. The arrogance to present this as something worthwhile is almost laughable. You''re not even worth my time. This conversation is beneath me. I expected nothing, and I''m still disappointed.', 
'contemptuous', 
'Superior disdain, looking down, dismissive superiority', 
0.15, 0.9, 0.85, 1.2, 
-0.7, 0.6, 0.75, 0.85);

-- ============================================================================
-- NEGATIVE - LOW ENERGY (61-68)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('sad_01', 
'I''ve been feeling so down lately. There''s this heaviness in my chest that won''t go away. Everything feels a little bit dimmer, a little bit harder. I miss how things used to be. I miss feeling okay. I don''t know when this sadness will lift, but right now it''s very present.', 
'sad', 
'General sorrow, low mood, emotional weight', 
0.1, 0.8, 0.65, 1.2, 
-0.7, 0.25, 0.3, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('melancholic_01', 
'There''s a certain beauty in this sadness, isn''t there? A bittersweet quality to remembering what was. The autumn light feels appropriate somehow. I find myself drawn to minor keys and rainy afternoons. This gentle sorrow has become my companion. It''s not sharp, just... present.', 
'melancholic', 
'Wistful sadness, poetic sorrow, aesthetic grief', 
0.08, 0.8, 0.6, 1.2, 
-0.5, 0.2, 0.2, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('discouraged_01', 
'Maybe I''m just not cut out for this. Every attempt seems to fall short of where it needs to be. I try and try but the results just aren''t there. What''s the point of continuing when nothing ever seems to work out? I''m starting to question whether this is worth pursuing anymore.', 
'discouraged', 
'Losing heart, diminishing motivation, doubt setting in', 
0.1, 0.8, 0.65, 1.2, 
-0.55, 0.3, 0.35, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('hopeless_01', 
'Nothing is going to change. I''ve accepted that now. No matter what I do, the outcome will be the same. There''s no path forward that leads anywhere different. I used to believe things could get better, but I''ve let go of that fantasy. This is just how it is. This is all there will ever be.', 
'hopeless', 
'Complete despair, no future visible, surrender to darkness', 
0.1, 0.85, 0.6, 1.2, 
-0.9, 0.15, 0.4, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('exhausted_01', 
'I have nothing left to give. Every ounce of energy has been drained from my body. My thoughts are moving through mud. I can barely keep my eyes open, barely form coherent sentences. I need to rest but even that feels like too much effort. I am completely and utterly spent.', 
'exhausted', 
'Total depletion, beyond tired, running on empty', 
0.06, 0.7, 0.5, 1.2, 
-0.4, 0.1, 0.15, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('apathetic_01', 
'I don''t really care either way anymore. Whatever happens, happens. It''s hard to muster any kind of investment in outcomes that used to matter to me. Everything feels flat, empty of meaning. I''m not sad exactly, just... hollow. The colors have all faded to grey.', 
'apathetic', 
'Emotional flatness, absence of caring, disconnected', 
0.05, 0.7, 0.55, 1.2, 
-0.3, 0.1, 0.1, 0.9);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('numb_01', 
'I know I should feel something about this. The old me would have had a strong reaction. But right now there''s just... nothing. An empty space where emotions should be. It''s like I''m watching everything from behind thick glass. I can see it but I can''t touch it or be touched by it.', 
'numb', 
'Emotional shutdown, dissociation from feeling, protective emptiness', 
0.05, 0.7, 0.5, 1.2, 
-0.2, 0.05, 0.05, 0.95);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('resigned_01', 
'It is what it is. I''ve stopped fighting against reality. There''s no point in raging against things I cannot change. I''ve made my peace with the situation, even if it''s not what I would have chosen. Acceptance isn''t the same as happiness, but it''s quieter than resistance.', 
'resigned', 
'Accepting the inevitable, surrendering struggle, weary peace', 
0.08, 0.75, 0.55, 1.2, 
-0.35, 0.2, 0.2, 0.9);

-- ============================================================================
-- NEGATIVE - ANXIETY/VULNERABILITY (69-77)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('anxious_01', 
'I can''t stop worrying about what might go wrong. My mind keeps racing through worst-case scenarios. What if it doesn''t work out? What if I''m not prepared? My chest feels tight and my thoughts keep spiraling. I know I''m probably overthinking but I can''t seem to stop.', 
'anxious', 
'Worried anticipation, nervous energy, racing thoughts', 
0.15, 0.85, 0.85, 1.2, 
-0.5, 0.75, 0.7, 0.5);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('worried_01', 
'Something doesn''t feel right and I can''t shake the feeling. I keep checking and rechecking but the concern is still there. Are you sure everything is okay? I need some reassurance here. My gut is telling me to be careful. Please just tell me there''s nothing to worry about.', 
'worried', 
'Concerned preoccupation, seeking reassurance, nagging doubt', 
0.12, 0.85, 0.8, 1.2, 
-0.4, 0.6, 0.55, 0.65);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('fearful_01', 
'I''m scared. I don''t want to admit it but I''m genuinely afraid. Something bad is going to happen, I can feel it. My hands are shaking and my heart is pounding. I want to run away but I''m frozen here. Please stay with me. I don''t want to face this alone.', 
'fearful', 
'Active fear, threat perceived, seeking safety', 
0.18, 0.9, 0.95, 1.2, 
-0.7, 0.8, 0.85, 0.5);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('panicked_01', 
'Oh god oh god oh god. What do we do? This is really happening. I can''t think straight. Everything is falling apart and I don''t know how to stop it. My heart is racing so fast. I need to get out of here. Someone help me, please, I can''t breathe properly!', 
'panicked', 
'Overwhelming fear, loss of control, fight-or-flight activated', 
0.25, 0.95, 1.1, 1.3, 
-0.85, 0.98, 0.95, 0.2);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('horrified_01', 
'No. No no no. This can''t be real. Tell me this isn''t happening. The image is burned into my mind and I can''t unsee it. This is the stuff of nightmares. I feel sick to my stomach. How could something like this exist? I don''t want to believe it.', 
'horrified', 
'Shock at witnessing something terrible, revulsion and fear combined', 
0.22, 0.95, 1.0, 1.2, 
-0.9, 0.9, 0.9, 0.3);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('insecure_01', 
'Do you actually like me? Or are you just being polite? I never know if I''m reading things correctly. Maybe I said something wrong. I always feel like I''m not quite good enough, like everyone else has something figured out that I''m missing. I''m sorry, I know I''m being difficult.', 
'insecure', 
'Self-doubt, seeking validation, questioning own worth', 
0.1, 0.8, 0.75, 1.2, 
-0.5, 0.5, 0.5, 0.6);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('vulnerable_01', 
'I''m going to tell you something I don''t share with many people. It makes me feel exposed just thinking about saying it out loud. But I trust you. Please be gentle with what I''m about to reveal. This is the part of me I usually keep hidden behind walls.', 
'vulnerable', 
'Exposed, opening up, risking rejection, tender openness', 
0.1, 0.85, 0.7, 1.2, 
-0.3, 0.45, 0.45, 0.7);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('embarrassed_01', 
'Oh no. Did everyone see that? I can''t believe that just happened. My face is burning. I wish the ground would swallow me up right now. How am I supposed to face people after this? Can we please just pretend that never happened? I''m mortified.', 
'embarrassed', 
'Social shame, wanting to hide, self-conscious exposure', 
0.15, 0.85, 0.85, 1.2, 
-0.55, 0.7, 0.65, 0.5);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('ashamed_01', 
'I can''t look you in the eye. What I did was wrong and I know it. There''s no excuse for my behavior. I''ve let myself down and I''ve let you down. The person I was in that moment isn''t who I want to be. I carry this weight everywhere now. I''m so deeply sorry.', 
'ashamed', 
'Deep moral failure, profound regret, internal judgment', 
0.1, 0.85, 0.75, 1.2, 
-0.7, 0.4, 0.55, 0.8);

-- ============================================================================
-- NEGATIVE - SOCIAL DISCOMFORT (78-85)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('guilty_01', 
'I should have been there. I should have done something differently. This is my fault and I know it. If only I had made a different choice, none of this would have happened. The responsibility weighs on me constantly. I don''t know how to make this right.', 
'guilty', 
'Responsibility for wrongdoing, moral burden, seeking atonement', 
0.1, 0.85, 0.7, 1.2, 
-0.6, 0.45, 0.5, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('awkward_01', 
'So... um... this is... yeah. I''m not really sure what to say here. The silence is getting uncomfortable. Should I say something? I feel like I''m making this worse. Maybe I should just... I don''t know. This is really uncomfortable for everyone, isn''t it?', 
'awkward', 
'Social discomfort, uncertain how to behave, stilted interaction', 
0.12, 0.8, 0.8, 1.2, 
-0.35, 0.55, 0.45, 0.45);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('defensive_01', 
'Wait, hold on. That''s not what I said at all. You''re twisting my words. I had perfectly good reasons for doing what I did. Why am I suddenly the bad guy here? I don''t appreciate being attacked like this. Let me explain myself before you jump to conclusions.', 
'defensive', 
'Self-protection, feeling accused, justifying actions', 
0.15, 0.85, 0.85, 1.2, 
-0.4, 0.7, 0.7, 0.7);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('dismissive_01', 
'Yeah, whatever. It''s not really that important anyway. I don''t see why we''re even discussing this. Can we move on to something that actually matters? I have better things to do with my time than go around in circles about something so trivial.', 
'dismissive', 
'Minimizing importance, brushing off, unconcerned rejection', 
0.1, 0.8, 0.75, 1.2, 
-0.45, 0.45, 0.4, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('condescending_01', 
'Oh, sweetie. Let me explain this in simpler terms so you can follow along. It''s actually quite basic once you understand the fundamentals, which apparently needs some work in your case. Don''t worry, not everyone can grasp these concepts quickly. I''ll be patient with you.', 
'condescending', 
'Talking down, patronizing, false helpfulness masking superiority', 
0.12, 0.85, 0.8, 1.2, 
-0.55, 0.55, 0.5, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('sarcastic_01', 
'Oh wow, what a brilliant observation. I never would have figured that out on my own. Thank you so much for enlightening me with your wisdom. Truly, I am forever in your debt. However did we manage before you came along to explain the obvious?', 
'sarcastic', 
'Mocking through false sincerity, biting humor, passive aggression', 
0.15, 0.85, 0.85, 1.2, 
-0.5, 0.6, 0.55, 0.8);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('cynical_01', 
'Of course they''re saying that. They always say that. It''s never actually going to happen, you know. People promise things all the time and then conveniently forget about it when it''s no longer useful to them. I''ve seen this play out too many times to believe otherwise.', 
'cynical', 
'Distrustful worldview, expecting the worst, jaded perspective', 
0.1, 0.8, 0.75, 1.2, 
-0.5, 0.45, 0.5, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('jealous_01', 
'Must be nice to have everything handed to you like that. Some of us have to actually work for what we have. I don''t understand why they always get the opportunities that I''ve been waiting for. It''s not fair. What do they have that I don''t? Why them and not me?', 
'jealous', 
'Envious comparison, wanting what others have, perceived unfairness', 
0.12, 0.85, 0.8, 1.2, 
-0.55, 0.6, 0.6, 0.7);

-- ============================================================================
-- CONFUSION/UNCERTAINTY (86-91)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('confused_01', 
'Wait, I don''t understand. Can you go over that again? I thought we were talking about something completely different. How did we get here? I''m completely lost now. None of this is making sense to me. What exactly are you trying to say?', 
'confused', 
'Mental disorientation, not comprehending, seeking clarity', 
0.12, 0.8, 0.8, 1.2, 
-0.25, 0.55, 0.4, 0.5);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('perplexed_01', 
'This doesn''t add up at all. By every measure, the outcome should have been different. I''ve checked and rechecked the logic but I can''t find where it breaks down. There''s something I''m missing here and it''s driving me crazy. How is this even possible?', 
'perplexed', 
'Deep puzzlement, confronting paradox, intellectual frustration', 
0.1, 0.8, 0.75, 1.2, 
-0.2, 0.6, 0.45, 0.6);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('uncertain_01', 
'I''m not entirely sure about this. It could go either way, honestly. I don''t want to commit to an answer without more information. There are too many variables I can''t account for. Maybe? I think so? But don''t quote me on that because I really don''t know.', 
'uncertain', 
'Lack of confidence in judgment, hedging, unwilling to commit', 
0.08, 0.75, 0.7, 1.2, 
-0.15, 0.45, 0.35, 0.6);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('hesitant_01', 
'I... I''m not sure I should. Something is making me pause here. Part of me wants to move forward but another part is holding back. Can I think about this a bit more? I don''t want to rush into a decision I might regret. Just give me a moment.', 
'hesitant', 
'Reluctance to act, internal conflict, seeking more time', 
0.08, 0.8, 0.7, 1.2, 
-0.2, 0.4, 0.4, 0.65);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('skeptical_01', 
'I''m going to need some evidence before I believe any of that. It sounds too good to be true, and in my experience, things that sound too good usually are. What''s the catch? Who''s backing this up? Have you verified these claims independently?', 
'skeptical', 
'Doubting claims, demanding proof, critical examination', 
0.1, 0.8, 0.75, 1.2, 
-0.25, 0.55, 0.45, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('distracted_01', 
'Sorry, what were you saying? I completely lost track there for a second. My mind keeps wandering to other things. I know I should be paying attention but I just can''t seem to focus right now. Can you start over? I promise I''ll try harder to listen this time.', 
'distracted', 
'Attention elsewhere, unable to concentrate, mentally scattered', 
0.1, 0.75, 0.75, 1.2, 
-0.1, 0.4, 0.2, 0.5);

-- ============================================================================
-- COMPLEX/NUANCED (92-100)
-- ============================================================================

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('surprised_01', 
'Whoa! I did not see that coming! Where did that come from? I had absolutely no idea! You completely caught me off guard. My whole understanding of the situation just shifted. I need a moment to process this because that changes everything.', 
'surprised', 
'Sudden unexpected information, rapid reorientation', 
0.2, 0.85, 0.95, 1.2, 
0.1, 0.85, 0.5, 0.25);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('shocked_01', 
'What?! No. No way. That can''t be right. Are you absolutely certain? This is... I don''t even know what to say. I''m literally speechless right now. My brain is not computing this information. How is this even real? I can''t process this.', 
'shocked', 
'Intense surprise, reality disruption, struggling to comprehend', 
0.22, 0.9, 1.0, 1.2, 
-0.2, 0.95, 0.7, 0.2);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('amazed_01', 
'This is absolutely incredible! I''ve never seen anything like this in my entire life! How is this even possible? It''s like something out of a dream. I''m completely blown away. Every time I think I understand, there''s another layer of wonder. This is extraordinary!', 
'amazed', 
'Positive overwhelm, wonder at discovery, expanded sense of possibility', 
0.2, 0.9, 0.95, 1.2, 
0.75, 0.9, 0.15, 0.4);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('bored_01', 
'Is this going to take much longer? I''ve completely zoned out at this point. Nothing interesting is happening here. I keep looking at the clock hoping time will move faster. Can we please do something else? Anything would be more engaging than this.', 
'bored', 
'Lack of stimulation, craving engagement, tedium', 
0.08, 0.75, 0.65, 1.2, 
-0.35, 0.2, 0.15, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('impatient_01', 
'Come on, come on, come on. How long is this going to take? We don''t have all day here. Can''t this go any faster? I hate waiting around like this. Every second feels like an eternity. Let''s get moving already. I''ve got things to do!', 
'impatient', 
'Urgency without outlet, frustrated waiting, time pressure', 
0.15, 0.85, 0.85, 1.2, 
-0.4, 0.75, 0.65, 0.65);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('restless_01', 
'I can''t seem to settle down. My leg keeps bouncing and my mind won''t stop racing. I need to move, to do something, but I don''t know what. Everything feels slightly agitated inside me. I''m not anxious exactly, just... unsettled. Something needs to change.', 
'restless', 
'Physical agitation, need for movement, unable to be still', 
0.12, 0.8, 0.8, 1.2, 
-0.2, 0.65, 0.4, 0.5);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('overwhelmed_01', 
'It''s all too much. There''s too much happening at once and I can''t keep up. Every direction I turn there''s another demand, another thing needing my attention. I don''t know where to start. I feel like I''m drowning in responsibilities. I need everything to stop for just one minute.', 
'overwhelmed', 
'Capacity exceeded, too many demands, system overload', 
0.15, 0.85, 0.85, 1.2, 
-0.6, 0.8, 0.75, 0.35);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('wistful_01', 
'I sometimes wonder what would have happened if I''d made different choices. Not with regret exactly, just... curiosity. Those paths not taken still shimmer in my imagination sometimes. There''s a sweetness in thinking about what might have been, even knowing I can''t go back.', 
'wistful', 
'Gentle longing for what''s past, bittersweet reflection', 
0.08, 0.8, 0.6, 1.2, 
-0.15, 0.25, 0.15, 0.85);

INSERT INTO prompt_templates (template_id, prompt_text, emotion_label, description, exaggeration, cfg_weight, temperature, repetition_penalty, target_valence, target_arousal, target_tension, target_stability) VALUES
('nostalgic_01', 
'Do you remember how things used to be? Those days feel so far away now, but also somehow close enough to touch. I can almost smell that old familiar air, hear those sounds again. Everything was different then. Part of me misses it terribly. Those were good times, weren''t they?', 
'nostalgic', 
'Affectionate memory, longing for the past, time distance', 
0.1, 0.8, 0.65, 1.2, 
0.3, 0.3, 0.1, 0.9);
