def _handle_shrine_input(self, action: str):
        """신전 상태에서의 입력 처리"""
        player_entity = self.world.get_player_entity()
        if not player_entity:
            self.state = GameState.PLAYING
            return
        
        # Step 0: 메인 메뉴 (복구 vs 강화)
        if self.shrine_enhance_step == 0:
            if action in [readchar.key.UP, '\x1b[A']:
                self.shrine_menu_index = max(0, self.shrine_menu_index - 1)
            elif action in [readchar.key.DOWN, '\x1b[B']:
                self.shrine_menu_index = min(1, self.shrine_menu_index + 1)
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                if self.shrine_menu_index == 0:
                    # 복구 선택
                    self._shrine_restore_all()
                    self._close_shrine()
                else:
                    # 강화 선택 - 장비 선택 단계로
                    self.shrine_enhance_step = 1
                    self.selected_equip_index = 0
        
        # Step 1: 강화할 장비 선택
        elif self.shrine_enhance_step == 1:
            inv = player_entity.get_component(InventoryComponent)
            if not inv:
                self.state = GameState.PLAYING
                return
            
            equipped_list = [(slot, item) for slot, item in inv.equipped.items() 
                           if item and isinstance(item, type(lambda: None).__self__.__class__.__bases__[0]) == False]
            
            if action in [readchar.key.UP, '\x1b[A']:
                self.selected_equip_index = max(0, self.selected_equip_index - 1)
            elif action in [readchar.key.DOWN, '\x1b[B']:
                if equipped_list:
                    self.selected_equip_index = min(len(equipped_list) - 1, self.selected_equip_index + 1)
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                if equipped_list and 0 <= self.selected_equip_index < len(equipped_list):
                    slot, item = equipped_list[self.selected_equip_index]
                    # 강화 시도
                    self._shrine_enhance_item(item)
                    self._close_shrine()
            elif action in ['b', 'B', readchar.key.ESC]:
                # 뒤로 가기
                self.shrine_enhance_step = 0
    
def _close_shrine(self):
        """신전 닫기 및 소멸 처리"""
        if self.active_shrine_id:
            shrine_ent = self.world.get_entity(self.active_shrine_id)
            if shrine_ent:
                shrine_comp = shrine_ent.get_component(ShrineComponent)
                if shrine_comp:
                    shrine_comp.is_used = True
                # 신전 엔티티 제거
                self.world.remove_entity(self.active_shrine_id)
        
        self.state = GameState.PLAYING
        self.active_shrine_id = None
        self.shrine_menu_index = 0
        self.shrine_enhance_step = 0
    
def _shrine_restore_all(self):
        """복구: 모든 내구도 + HP/MP/Stamina 완전 회복"""
        player_entity = self.world.get_player_entity()
        if not player_entity:
            return
        
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        
        if stats:
            # HP/MP/Stamina 회복
            stats.current_hp = stats.max_hp
            stats.current_mp = stats.max_mp
            stats.current_stamina = stats.max_stamina
        
        if inv:
            # 모든 장비 내구도 회복
            for slot, item in inv.equipped.items():
                if item and hasattr(item, 'max_durability') and item.max_durability > 0:
                    item.current_durability = item.max_durability
        
        self.world.event_manager.push(MessageEvent(_("신성한 힘이 당신을 완전히 회복시켰습니다!")))
        self.world.event_manager.push(SoundEvent("LEVEL_UP"))
        self._recalculate_stats()
    
def _shrine_enhance_item(self, item):
        """강화: 아이템 등급 +1, 성공/실패 처리"""
        import random
        
        current_level = getattr(item, 'enhancement_level', 0)
        
        # 성공률 계산
        if current_level <= 3:
            success_rate = 0.9 - (current_level * 0.1)  # 90%, 80%, 70%
        elif current_level <= 6:
            success_rate = 0.5 - ((current_level - 4) * 0.1)  # 50%, 40%, 30%
        elif current_level <= 9:
            success_rate = 0.2 - ((current_level - 7) * 0.05)  # 20%, 15%, 10%
        elif current_level == 10:
            success_rate = 0.05  # 5%
        else:
            self.world.event_manager.push(MessageEvent(_("이미 최대 강화 등급입니다!")))
            return
        
        roll = random.random()
        
        if roll < success_rate:
            # 성공!
            item.enhancement_level += 1
            
            # 랜덤 affix 효과 증가 (5~10%)
            boost_pct = random.uniform(0.05, 0.10)
            
            # 접두사/접미사 효과 중 하나 랜덤 선택하여 증가
            possible_stats = []
            if hasattr(item, 'prefix_id') and item.prefix_id:
                possible_stats.extend(['damage_percent', 'to_hit_bonus', 'res_fire', 'res_ice', 'res_lightning', 'res_poison', 'res_all'])
            if hasattr(item, 'suffix_id') and item.suffix_id:
                possible_stats.extend(['str_bonus', 'dex_bonus', 'mag_bonus', 'vit_bonus', 'hp_bonus', 'mp_bonus', 'damage_max_bonus', 'life_leech', 'attack_speed'])
            
            if possible_stats:
                stat_to_boost = random.choice(possible_stats)
                current_val = getattr(item, stat_to_boost, 0)
                if current_val > 0:
                    boost = int(current_val * boost_pct)
                    if boost < 1: boost = 1
                    setattr(item, stat_to_boost, current_val + boost)
            
            # 이름 업데이트
            base_name = item.name
            if '+' in base_name:
                # 기존 강화 표시 제거
                base_name = base_name.split('+')[0].strip()
            item.name = f"+{item.enhancement_level} {base_name}"
            
            self.world.event_manager.push(MessageEvent(_("강화 성공! {}").format(item.name)))
            self.world.event_manager.push(SoundEvent("LEVEL_UP"))
        else:
            # 실패!
            if current_level <= 3:
                # 안전: 내구도 절반 감소
                if hasattr(item, 'current_durability') and item.max_durability > 0:
                    item.current_durability = max(0, item.current_durability // 2)
                self.world.event_manager.push(MessageEvent(_("강화 실패... {}의 내구도가 감소했습니다.").format(item.name)))
            elif current_level <= 6:
                # 파손: 내구도 0
                if hasattr(item, 'current_durability'):
                    item.current_durability = 0
                self.world.event_manager.push(MessageEvent(_("강화 실패! {}이(가) 파손되었습니다!").format(item.name)))
            else:
                # 소멸: 아이템 제거
                player_entity = self.world.get_player_entity()
                if player_entity:
                    inv = player_entity.get_component(InventoryComponent)
                    if inv:
                        # 장착 해제
                        for slot, equipped_item in list(inv.equipped.items()):
                            if equipped_item == item:
                                inv.equipped[slot] = None
                self.world.event_manager.push(MessageEvent(_("강화 실패! {}이(가) 산산조각 났습니다...").format(item.name)))
            
            self.world.event_manager.push(SoundEvent("BREAK"))
        
        self._recalculate_stats()
