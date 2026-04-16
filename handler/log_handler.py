from astrbot.api.event import filter, AstrMessageEvent

from ..component.output import get_output


class LogMixin:

    @filter.command_group("log")
    async def log(self, event: AstrMessageEvent):
        pass

    @log.command("new")
    async def cmd_log_new(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        parts = event.message_str.strip().split()
        name = parts[2] if len(parts) >= 3 else None
        ok, info = await self.logger_core.new_session(group, name)
        yield event.plain_result(info)

    @log.command("end")
    async def cmd_log_end(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        ok, result = await self.logger_core.end_session(group)

        if not ok:
            yield event.plain_result(result)
            return

        name, sec = result

        try:
            from astrbot.api.message_components import File

            ok, file_path = await self.logger_core.export_session(group, sec, name)
            if not ok:
                yield event.plain_result(get_output("log.export_failed", error=file_path))
                return

            file_name = f"{group}_{name}.json"
            yield event.chain_result([File(file=file_path, name=file_name)])
            yield event.plain_result(
                get_output("log.session_exported", session_name=name, file_name=file_name)
            )
        except Exception as e:
            yield event.plain_result(
                get_output("log.send_file_failed", error=str(e))
            )

    @log.command("off")
    async def cmd_log_off(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        ok, info = await self.logger_core.pause_sessions(group)
        yield event.plain_result(info)

    @log.command("on")
    async def cmd_log_on(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        parts = event.message_str.strip().split()
        name = parts[2] if len(parts) >= 3 else None
        ok, info = await self.logger_core.resume_session(group, name)
        yield event.plain_result(info)

    @log.command("list")
    async def cmd_log_list(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        lines = await self.logger_core.list_sessions(group)
        yield event.plain_result("\n".join(lines))

    @log.command("del")
    async def cmd_log_del(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            yield event.plain_result(get_output("log.delete_error"))
            return
        name = parts[2]
        ok, info = await self.logger_core.delete_session(group, name)
        yield event.plain_result(info)

    @log.command("get")
    async def cmd_log_get(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        parts = event.message_str.strip().split()
        name = parts[2] if len(parts) >= 3 else None
        grp = await self.logger_core.load_group(group)
        if name not in grp:
            yield event.plain_result(
                get_output("log.session_not_found", session_name=name)
            )
            return
        sec = grp[name]
        ok, file_path = await self.logger_core.export_session(group, sec, name)
        if ok:
            try:
                from astrbot.api.message_components import File
                file_name = f"{group}_{name}.json"
                yield event.chain_result([File(file=file_path, name=file_name)])
            except Exception as e:
                yield event.plain_result(get_output("log.send_file_failed", error=str(e)))
        else:
            yield event.plain_result(get_output("log.export_failed", error=file_path))

    @log.command("stat")
    async def cmd_log_stat(self, event: AstrMessageEvent):
        group = event.message_obj.group_id
        parts = event.message_str.strip().split()
        name = parts[2] if len(parts) >= 3 else None
        all_flag = len(parts) >= 4 and parts[3] == "--all"
        lines = await self.logger_core.stat_sessions(group, name, all_flag)
        yield event.plain_result("\n".join(lines))
