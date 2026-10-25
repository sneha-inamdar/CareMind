import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class WaveformPainter extends CustomPainter {
  final List<double> samples;
  final Color color;
  final String label;
  final String unit;

  WaveformPainter({
    required this.samples,
    required this.color,
    required this.label,
    required this.unit,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final bgPaint = Paint()..color = const Color(0xFF0F172A);
    final gridPaint = Paint()
      ..color = const Color(0xFF1E293B)
      ..strokeWidth = 1.0;

    // Draw background
    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    canvas.drawRect(rect, bgPaint);

    // Draw grid lines
    const int gridCols = 8;
    const int gridRows = 4;
    for (int i = 1; i < gridCols; i++) {
      final x = size.width * (i / gridCols);
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (int j = 1; j < gridRows; j++) {
      final y = size.height * (j / gridRows);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    if (samples.isEmpty) {
      final textPainter = TextPainter(
        text: TextSpan(
          text: '$label: Signal Unavailable',
          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(canvas, Offset(10, size.height / 2 - 6));
      return;
    }

    // Min/Max scaling
    double minVal = samples.reduce((a, b) => a < b ? a : b);
    double maxVal = samples.reduce((a, b) => a > b ? a : b);
    if ((maxVal - minVal).abs() < 1e-5) {
      maxVal += 1.0;
      minVal -= 1.0;
    }

    final path = Path();
    final stepX = size.width / (samples.length - 1);
    final padding = 12.0;
    final usableHeight = size.height - (padding * 2);

    for (int i = 0; i < samples.length; i++) {
      final normY = (samples[i] - minVal) / (maxVal - minVal);
      final x = i * stepX;
      final y = size.height - padding - (normY * usableHeight);

      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    final linePaint = Paint()
      ..color = color
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    canvas.drawPath(path, linePaint);

    // Draw overlay label
    final labelPainter = TextPainter(
      text: TextSpan(
        children: [
          TextSpan(
            text: '$label ',
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 11,
            ),
          ),
          TextSpan(
            text: '($unit)',
            style: const TextStyle(color: Colors.white70, fontSize: 10),
          ),
        ],
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    labelPainter.paint(canvas, const Offset(8, 6));
  }

  @override
  bool shouldRepaint(covariant WaveformPainter oldDelegate) {
    return oldDelegate.samples != samples || oldDelegate.color != color;
  }
}

class WaveformCard extends StatelessWidget {
  final String title;
  final String unit;
  final List<double> samples;
  final Color color;
  final bool isMonitored;

  const WaveformCard({
    super.key,
    required this.title,
    required this.unit,
    required this.samples,
    required this.color,
    required this.isMonitored,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.border),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isMonitored)
              Container(
                height: 90,
                width: double.infinity,
                color: const Color(0xFF1E293B),
                alignment: Alignment.center,
                child: Text(
                  '$title • Not monitored',
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              )
            else
              SizedBox(
                height: 95,
                width: double.infinity,
                child: CustomPaint(
                  painter: WaveformPainter(
                    samples: samples,
                    color: color,
                    label: title,
                    unit: unit,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
