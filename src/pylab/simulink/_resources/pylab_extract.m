% SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
% 
% SPDX-License-Identifier: GPL-3.0-or-later

function [result] = pylab_extract(out, var)
  % Extract variable ``var`` from each member of ``out`` and concat them
  % as timeseries.
  for i=1:length(out)
    next = getfield(out(i), var)

    if i == 1
      result = next
    else
      % Remove overlap between timeseries to prevent double writes. We
      % remove the "left" copy of a double write so that the effect of
      % commands issued to be executed at a breakpoint is immediately
      % logged.
      if any(next.Time == result.Time(end))
        result = delsample(result, 'Value', result.Time(end))
      end
      result = append(result, next)
    end
  end
% endfunction
