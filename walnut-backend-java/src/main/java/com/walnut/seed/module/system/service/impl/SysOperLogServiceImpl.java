package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.hutool.core.util.ArrayUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.ip.AddressUtils;
import com.walnut.seed.common.log.event.OperLogEvent;
import com.walnut.seed.module.system.domain.entity.SysOperLog;
import com.walnut.seed.module.system.domain.req.SysOperLogReq;
import com.walnut.seed.module.system.domain.resp.SysOperLogResp;
import com.walnut.seed.module.system.mapper.SysOperLogMapper;
import com.walnut.seed.module.system.service.SysOperLogService;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

/**
 * 操作日志 服务层处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysOperLogServiceImpl implements SysOperLogService {

    private final SysOperLogMapper baseMapper;

    /**
     * 操作日志记录
     *
     * @param operLogEvent 操作日志事件
     */
    @Async("walnutExecutor")
    @EventListener
    public void recordOper(OperLogEvent operLogEvent) {
        SysOperLogReq operLog = MapstructUtils.convert(operLogEvent, SysOperLogReq.class);
        // 远程查询操作地点
        operLog.setOperLocation(AddressUtils.getRealAddressByIP(operLog.getOperIp()));
        insertOperlog(operLog);
    }

    @Override
    public PageResult<SysOperLogResp> selectPageOperLogList(SysOperLogReq operLog) {
        LambdaQueryWrapper<SysOperLog> lqw = buildQueryWrapper(operLog);
        if (StringUtils.isBlank(operLog.getOrderByColumn())) {
            lqw.orderByDesc(SysOperLog::getId);
        }
        Page<SysOperLogResp> page = baseMapper.selectVoPage(operLog.buildPage(), lqw);
        return PageResult.of(page);
    }

    private LambdaQueryWrapper<SysOperLog> buildQueryWrapper(SysOperLogReq req) {
        return new LambdaQueryWrapper<SysOperLog>()
            .like(StringUtils.isNotBlank(req.getOperIp()), SysOperLog::getOperIp, req.getOperIp())
            .like(StringUtils.isNotBlank(req.getTitle()), SysOperLog::getTitle, req.getTitle())
            .eq(req.getBusinessType() != null && req.getBusinessType() > 0,
                SysOperLog::getBusinessType, req.getBusinessType())
            .func(f -> {
                if (ArrayUtil.isNotEmpty(req.getBusinessTypes())) {
                    f.in(SysOperLog::getBusinessType, Arrays.asList(req.getBusinessTypes()));
                }
            })
            .eq(req.getStatus() != null,
                SysOperLog::getStatus, req.getStatus())
            .like(StringUtils.isNotBlank(req.getOperName()), SysOperLog::getOperName, req.getOperName())
            .between(req.getBeginTime() != null && req.getEndTime() != null,
                SysOperLog::getOperTime, req.getBeginTime(), req.getEndTime());
    }

    @Override
    public void insertOperlog(SysOperLogReq req) {
        SysOperLog operLog = MapstructUtils.convert(req, SysOperLog.class);
        operLog.setOperTime(new Date());
        baseMapper.insert(operLog);
    }

    @Override
    public List<SysOperLogResp> selectOperLogList(SysOperLogReq operLog) {
        LambdaQueryWrapper<SysOperLog> lqw = buildQueryWrapper(operLog);
        return baseMapper.selectVoList(lqw.orderByDesc(SysOperLog::getId));
    }

    @Override
    public int deleteOperLogByIds(Long[] operIds) {
        return baseMapper.deleteByIds(Arrays.asList(operIds));
    }

    @Override
    public SysOperLogResp selectOperLogById(Long operId) {
        return baseMapper.selectVoById(operId);
    }

    @Override
    public void cleanOperLog() {
        baseMapper.delete(new LambdaQueryWrapper<>());
    }
}
