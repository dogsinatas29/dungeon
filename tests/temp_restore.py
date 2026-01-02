            else:
                slot_num = 10 if num == 0 else num
                self.world.event_manager.push(MessageEvent(f"{slot_num}번 스킬 슬롯이 비어있습니다."))
                return False
        return False
