package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.hutool.core.util.ObjectUtil;
import cn.hutool.http.useragent.UserAgent;
import cn.hutool.http.useragent.UserAgentUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.constant.Constants;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.ServletUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.ip.AddressUtils;
import com.walnut.seed.common.log.event.LogininforEvent;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.entity.SysLogininfor;
import com.walnut.seed.module.system.domain.req.SysLogininforReq;
import com.walnut.seed.module.system.domain.resp.SysClientResp;
import com.walnut.seed.module.system.domain.resp.SysLogininforResp;
import com.walnut.seed.module.system.mapper.SysLogininforMapper;
import com.walnut.seed.module.system.service.SysClientService;
import com.walnut.seed.module.system.service.SysLogininforService;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

/**
 * 系统访问日志情况信息 服务层处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Slf4j
@Service
public class SysLogininforServiceImpl implements SysLogininforService {

    private final SysLogininforMapper baseMapper;

    private final SysClientService clientService;

    /**
     * 记录登录信息
     *
     * @param logininforEvent 登录事件
     */
    @Async("walnutExecutor")
    @EventListener
    public void recordLogininfor(LogininforEvent logininforEvent) {
        HttpServletRequest request = logininforEvent.getRequest();
        final UserAgent userAgent = UserAgentUtil.parse(request.getHeader("User-Agent"));
        final String ip = ServletUtils.getClientIP(request);
        // 客户端信息
        String clientId = request.getHeader(LoginHelper.CLIENT_KEY);
        SysClientResp client = null;
        if (StringUtils.isNotBlank(clientId)) {
            client = clientService.queryByClientId(clientId);
        }

        String address = AddressUtils.getRealAddressByIP(ip);
        StringBuilder s = new StringBuilder();
        s.append(getBlock(ip));
        s.append(address);
        s.append(getBlock(logininforEvent.getUsername()));
        s.append(getBlock(logininforEvent.getStatus()));
        s.append(getBlock(logininforEvent.getMessage()));
        // 打印信息到日志
        log.info(s.toString(), logininforEvent.getArgs());
        // 获取客户端操作系统
        String os = userAgent.getOs().getName();
        // 获取客户端浏览器
        String browser = userAgent.getBrowser().getName();
        // 封装对象
        SysLogininforReq logininfor = new SysLogininforReq();
        logininfor.setUserName(logininforEvent.getUsername());
        if (ObjectUtil.isNotNull(client)) {
            logininfor.setClientKey(client.getClientKey());
            logininfor.setDeviceType(client.getDeviceType());
        }
        logininfor.setIpaddr(ip);
        logininfor.setLoginLocation(address);
        logininfor.setBrowser(browser);
        logininfor.setOs(os);
        logininfor.setMsg(logininforEvent.getMessage());
        // 日志状态
        if (StringUtils.equalsAny(logininforEvent.getStatus(), Constants.LOGIN_SUCCESS, Constants.LOGOUT, Constants.REGISTER)) {
            logininfor.setStatus(Constants.SUCCESS);
        } else if (Constants.LOGIN_FAIL.equals(logininforEvent.getStatus())) {
            logininfor.setStatus(Constants.FAIL);
        }
        // 插入数据
        insertLogininfor(logininfor);
    }

    private String getBlock(Object msg) {
        if (msg == null) {
            msg = "";
        }
        return "[" + msg.toString() + "]";
    }

    @Override
    public PageResult<SysLogininforResp> selectPageLogininforList(SysLogininforReq req) {
        LambdaQueryWrapper<SysLogininfor> lqw = new LambdaQueryWrapper<SysLogininfor>()
            .like(StringUtils.isNotBlank(req.getIpaddr()), SysLogininfor::getIpaddr, req.getIpaddr())
            .eq(StringUtils.isNotBlank(req.getStatus()), SysLogininfor::getStatus, req.getStatus())
            .like(StringUtils.isNotBlank(req.getUserName()), SysLogininfor::getUserName, req.getUserName())
            .between(req.getBeginTime() != null && req.getEndTime() != null,
                SysLogininfor::getLoginTime, req.getBeginTime(), req.getEndTime());
        if (StringUtils.isBlank(req.getOrderByColumn())) {
            lqw.orderByDesc(SysLogininfor::getId);
        }
        Page<SysLogininforResp> page = baseMapper.selectVoPage(req.buildPage(), lqw);
        return PageResult.of(page);
    }

    @Override
    public void insertLogininfor(SysLogininforReq req) {
        SysLogininfor logininfor = MapstructUtils.convert(req, SysLogininfor.class);
        logininfor.setLoginTime(new Date());
        baseMapper.insert(logininfor);
    }

    @Override
    public List<SysLogininforResp> selectLogininforList(SysLogininforReq logininfor) {
        return baseMapper.selectVoList(new LambdaQueryWrapper<SysLogininfor>()
            .like(StringUtils.isNotBlank(logininfor.getIpaddr()), SysLogininfor::getIpaddr, logininfor.getIpaddr())
            .eq(StringUtils.isNotBlank(logininfor.getStatus()), SysLogininfor::getStatus, logininfor.getStatus())
            .like(StringUtils.isNotBlank(logininfor.getUserName()), SysLogininfor::getUserName, logininfor.getUserName())
            .between(logininfor.getBeginTime() != null && logininfor.getEndTime() != null,
                SysLogininfor::getLoginTime, logininfor.getBeginTime(), logininfor.getEndTime())
            .orderByDesc(SysLogininfor::getId));
    }

    @Override
    public int deleteLogininforByIds(Long[] infoIds) {
        return baseMapper.deleteByIds(Arrays.asList(infoIds));
    }

    @Override
    public void cleanLogininfor() {
        baseMapper.delete(new LambdaQueryWrapper<>());
    }
}
